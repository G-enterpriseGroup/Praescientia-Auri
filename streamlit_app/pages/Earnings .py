import re
import requests
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime

# =========================
# CONFIG (PASTE YOUR KEY LOCALLY)
# =========================
FMP_API_KEY = "38psbXnud9teC46Q4zBBMzgqzNaETsNe"

BASE = "https://financialmodelingprep.com/stable/earnings-calendar"


# -------------------------
# Helpers
# -------------------------
def _normalize_ticker(t: str) -> str:
    t = (t or "").strip().upper()
    # Normalize common share-class tickers: BRK.B -> BRK-B
    t = t.replace(".", "-")
    t = t.replace(" ", "")
    return t


def _parse_tickers(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[,\n\r\t ]+", text.strip())
    tickers = [_normalize_ticker(p) for p in parts if p.strip()]
    # de-dupe while preserving order
    seen = set()
    out = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


@st.cache_data(show_spinner=False, ttl=6 * 60 * 60)
def _fetch_calendar(from_date: str, to_date: str, api_key: str) -> list[dict]:
    params = {"apikey": api_key, "from": from_date, "to": to_date}
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    return r.json() if r.text else []


def next_earnings_dates(tickers: list[str], days_ahead: int) -> pd.DataFrame:
    tickers = [_normalize_ticker(t) for t in tickers if str(t).strip()]
    if not tickers:
        return pd.DataFrame(columns=["Ticker", "NextEarningsDate", "DaysUntil", "Time"])

    today = date.today()
    to_day = today + timedelta(days=int(days_ahead))

    rows = _fetch_calendar(today.isoformat(), to_day.isoformat(), FMP_API_KEY)

    wanted = set(tickers)
    next_map: dict[str, tuple[str, str | None]] = {}  # ticker -> (date_str, time_str)

    for row in rows:
        sym = _normalize_ticker(row.get("symbol"))
        if sym not in wanted:
            continue

        d = row.get("date")  # YYYY-MM-DD
        if not d:
            continue

        tm = row.get("time")  # may be None
        if (sym not in next_map) or (d < next_map[sym][0]):
            next_map[sym] = (d, tm)

    out = []
    for t in tickers:
        d, tm = next_map.get(t, (None, None))
        days_until = ""
        if d:
            try:
                days_until = (datetime.strptime(d, "%Y-%m-%d").date() - today).days
            except Exception:
                days_until = ""
        out.append({"Ticker": t, "NextEarningsDate": d, "DaysUntil": days_until, "Time": tm})

    return pd.DataFrame(out)


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="Earnings Dates (FMP)", layout="wide")
st.title("Earnings Dates (FMP)")

if not FMP_API_KEY or FMP_API_KEY.strip() in ("", "PASTE_YOUR_FMP_KEY_HERE"):
    st.error('Missing API key. Paste it into FMP_API_KEY at the top of this file (locally).')
    st.stop()

colA, colB = st.columns([2, 1])

with colA:
    tickers_text = st.text_area(
        "Tickers (comma, space, or newline separated)",
        value="AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,BRK.B,AVGO,JPM",
        height=120,
    )
    uploaded = st.file_uploader("Optional: upload a .txt/.csv with tickers", type=["txt", "csv"])

with colB:
    days_ahead = st.slider("Look-ahead window (days)", min_value=30, max_value=365, value=240, step=30)
    run = st.button("Get earnings dates", type="primary")

tickers = _parse_tickers(tickers_text)

if uploaded is not None:
    try:
        content = uploaded.getvalue().decode("utf-8", errors="ignore")
        file_tickers = _parse_tickers(content)
        if file_tickers:
            tickers = file_tickers
            st.info(f"Loaded {len(tickers)} tickers from file.")
    except Exception as e:
        st.warning(f"Could not read uploaded file: {e}")

if run:
    try:
        df = next_earnings_dates(tickers, days_ahead=days_ahead)
        st.subheader("Results")
        st.dataframe(df, use_container_width=True)

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="next_earnings.csv",
            mime="text/csv",
        )
    except requests.HTTPError as e:
        st.error(f"API error: {e}")
    except Exception as e:
        st.error(f"Error: {e}")
