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

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Earnings Dates (FMP)", layout="wide")

# =========================
# BLOOMBERG-STYLE ORANGE THEME + 3D BUTTON + HTML TABLE
# =========================
CSS = """
<style>
/* Global */
html, body, [class*="css"] {
  background: #000000 !important;
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}

/* Reduce padding a bit */
.block-container { padding-top: 1.0rem; padding-bottom: 1.0rem; }

/* Titles */
h1, h2, h3, h4, h5, h6 {
  color: #ff9900 !important;
  letter-spacing: 0.4px;
}

/* Inputs */
textarea, input, div[data-baseweb="input"] input {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 10px !important;
}

/* Slider */
div[data-baseweb="slider"] * {
  color: #ff9900 !important;
}

/* 3D Orange Button */
div.stButton > button {
  background: linear-gradient(180deg, #ffb84d 0%, #ff9900 55%, #e07f00 100%) !important;
  color: #000000 !important;
  border: 2px solid #ffcc80 !important;
  border-radius: 12px !important;
  font-weight: 900 !important;
  letter-spacing: 0.6px !important;
  padding: 0.60rem 1.00rem !important;
  box-shadow:
    0 7px 0 #a65a00,
    0 12px 22px rgba(0,0,0,0.55) !important;
  transform: translateY(0px);
}

div.stButton > button:hover {
  filter: brightness(1.03);
}

div.stButton > button:active {
  transform: translateY(6px);
  box-shadow:
    0 1px 0 #a65a00,
    0 6px 14px rgba(0,0,0,0.45) !important;
}

/* Download button matches theme */
div.stDownloadButton > button {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 12px !important;
  font-weight: 900 !important;
  padding: 0.55rem 0.95rem !important;
}

/* HTML table styling */
.bb-table-wrap {
  background: #050505;
  border: 2px solid #ff9900;
  border-radius: 14px;
  padding: 12px;
  box-shadow: 0 14px 30px rgba(0,0,0,0.55);
}

table.bb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 15px;
}

table.bb-table thead th {
  background: #0b0b0b;
  color: #ff9900;
  border-bottom: 2px solid #ff9900;
  padding: 10px;
  text-align: left;
}

table.bb-table tbody td {
  padding: 10px;
  border-bottom: 1px solid rgba(255,153,0,0.35);
  color: #ffcc80;
}

table.bb-table tbody tr:hover td {
  background: rgba(255,153,0,0.10);
  color: #ffddaa;
}

/* Small badges */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border: 1px solid #ff9900;
  border-radius: 999px;
  color: #ff9900;
  background: rgba(255,153,0,0.08);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.3px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# -------------------------
# Helpers
# -------------------------
def _normalize_ticker(t: str) -> str:
    t = (t or "").strip().upper()
    t = t.replace(".", "-")  # BRK.B -> BRK-B
    t = t.replace(" ", "")
    return t


def _parse_tickers(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[,\n\r\t ]+", text.strip())
    tickers = [_normalize_ticker(p) for p in parts if p.strip()]
    seen = set()
    out = []
    for x in tickers:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _fmt_mmmm_dd_yyyy(d: str | None) -> str:
    """Convert 'YYYY-MM-DD' -> 'MMMM,DD,YYYY' (e.g., January,02,2026)."""
    if not d:
        return ""
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        return dt.strftime("%B,%d,%Y")
    except Exception:
        return d  # fallback


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
    next_map: dict[str, tuple[str, str | None]] = {}

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
        out.append(
            {
                "Ticker": t,
                "NextEarningsDate": _fmt_mmmm_dd_yyyy(d),
                "DaysUntil": days_until,
                "Time": tm or "",
            }
        )

    return pd.DataFrame(out)


def df_to_bb_html(df: pd.DataFrame) -> str:
    # Ensure consistent ordering
    df = df.copy()
    cols = ["Ticker", "NextEarningsDate", "DaysUntil", "Time"]
    df = df[cols] if all(c in df.columns for c in cols) else df

    html = df.to_html(index=False, escape=True, classes=["bb-table"])
    return f'<div class="bb-table-wrap">{html}</div>'


# =========================
# Streamlit UI
# =========================
st.title("Earnings Dates")
st.markdown('<span class="badge">FMP Earnings Calendar</span>', unsafe_allow_html=True)

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
    run = st.button("GET EARNINGS DATES")

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

        st.subheader("Results (HTML)")
        st.markdown(df_to_bb_html(df), unsafe_allow_html=True)

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "DOWNLOAD CSV",
            data=csv_bytes,
            file_name="next_earnings.csv",
            mime="text/csv",
        )

    except requests.HTTPError as e:
        st.error(f"API error: {e}")
    except Exception as e:
        st.error(f"Error: {e}")
