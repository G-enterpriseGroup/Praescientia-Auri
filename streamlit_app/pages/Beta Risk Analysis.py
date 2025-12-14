import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta

# ----------------------------
# Page + Theme (90s Orange)
# ----------------------------
st.set_page_config(page_title="Mid-Price Drop Comparator", layout="wide")

CSS = """
<style>
html, body, [class*="css"]  {
  background: #000000 !important;
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}
.block-container { padding-top: 1.0rem; padding-bottom: 1.0rem; }

h1, h2, h3, h4, h5, h6 {
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
  letter-spacing: 0.5px;
}

input, textarea {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
  box-shadow: none !important;
}

/* Date + number inputs */
div[data-baseweb="input"] > div {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}

/* Buttons */
.stButton > button {
  background: #000000 !important;
  color: #ff9900 !important;
  border: 3px solid #ff9900 !important;
  border-radius: 0px !important;
  font-family: "Courier New", Courier, monospace !important;
  padding: 0.6rem 1.0rem !important;
  box-shadow: none !important;
  text-transform: uppercase;
}
.stButton > button:hover { background: #111111 !important; }

[data-testid="stDataFrame"] {
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}

hr { border: 0; border-top: 2px dashed #ff9900; }
a { color: #ffcc66 !important; }
a:hover { color: #ffffff !important; }

div[data-testid="stMetric"] {
  border: 2px solid #ff9900;
  padding: 10px;
  border-radius: 0px;
  background: #050505;
}

/* Hide sidebar completely */
section[data-testid="stSidebar"] { display: none !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.title("MID-PRICE DROP COMPARATOR (DAILY MID = (HIGH + LOW) / 2)")
st.caption("Table math uses Mid = (High + Low) / 2 • Chart is NORMALIZED (each ticker starts at 100)")
st.markdown("---")

# ----------------------------
# Helpers
# ----------------------------
def parse_tickers_space(raw: str) -> list[str]:
    if not raw:
        return []
    parts = [p.strip().upper() for p in raw.split() if p.strip()]
    seen = set()
    out = []
    for t in parts:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

def _uppercase_ticker_input():
    # auto-caps the ticker text input as you type (on change)
    k = "raw_tickers"
    v = st.session_state.get(k, "")
    if isinstance(v, str):
        st.session_state[k] = v.upper()

def _parse_amount_with_commas(s: str):
    if s is None:
        return None
    try:
        cleaned = str(s).strip().replace(",", "").replace("$", "")
        if cleaned == "":
            return None
        val = float(cleaned)
        if val < 0:
            return None
        return val
    except Exception:
        return None

def _format_amount_with_commas(s: str):
    val = _parse_amount_with_commas(s)
    if val is None:
        return s
    return f"{val:,.2f}"

@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_ohlc_window(ticker: str, start_dt: date, end_dt: date) -> pd.DataFrame:
    s = datetime.combine(start_dt, datetime.min.time()) - timedelta(days=10)
    e = datetime.combine(end_dt, datetime.min.time()) + timedelta(days=1)

    df = yf.download(
        tickers=ticker,
        start=s.strftime("%Y-%m-%d"),
        end=e.strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
        threads=True,
    )
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)

    keep = [c for c in ["High", "Low", "Open", "Close", "Volume"] if c in df.columns]
    return df[keep]

def nearest_prev_trading_row(df: pd.DataFrame, target_dt: date):
    if df.empty:
        return None
    eligible = df[df.index <= pd.to_datetime(target_dt)]
    return None if eligible.empty else eligible.iloc[-1]

def fmt_money(x):
    if x is None or pd.isna(x): return "—"
    return f"(${abs(x):,.2f})" if x < 0 else f"${x:,.2f}"

def fmt_pct(x):
    if x is None or pd.isna(x): return "—"
    return f"{x * 100:.2f}%"

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None

# ----------------------------
# INPUTS (ENTER RUNS)
# ----------------------------
st.subheader("INPUTS")

# Initialize defaults once (so the text inputs keep value nicely)
if "raw_tickers" not in st.session_state:
    st.session_state["raw_tickers"] = "CLOZ SPY"
if "amount_str" not in st.session_state:
    st.session_state["amount_str"] = "80,000.00"

with st.form("run_form", clear_on_submit=False):
    c1, c2, c3, c4 = st.columns([2.2, 1.3, 1.3, 1.2])

    with c1:
        raw_tickers = st.text_input(
            "TICKERS (space-separated)",
            key="raw_tickers",
            on_change=_uppercase_ticker_input,
        )

    with c2:
        amount_str = st.text_input(
            "AMOUNT ($)",
            key="amount_str",
            help="You can type commas like 80,000.00",
        )

    with c3:
        start_date = st.date_input("START DATE", value=date(2025, 2, 24))
    with c4:
        end_date = st.date_input("END DATE", value=date(2025, 4, 7))

    st.markdown("")
    run = st.form_submit_button("RUN COMPARISON")

# Parse + reformat amount (commas) AFTER the form so typing stays smooth
amount = _parse_amount_with_commas(st.session_state.get("amount_str", ""))
if amount is not None:
    st.session_state["amount_str"] = _format_amount_with_commas(st.session_state.get("amount_str", ""))

tickers = parse_tickers_space(raw_tickers)

# ----------------------------
# Main
# ----------------------------
if run:
    if not tickers:
        st.error("Enter at least one ticker (space-separated). Example: CLOZ SPY")
        st.stop()

    if amount is None:
        st.error("Enter a valid AMOUNT ($). Example: 80,000 or 80,000.00")
        st.stop()

    if end_date < start_date:
        st.error("End Date must be on/after Start Date.")
        st.stop()

    st.write(f"**Tickers (cleaned to UPPERCASE):** {' '.join(tickers)}")

    summary_rows = []
    chart_rows = []
    errors = []

    with st.spinner("Pulling daily High/Low data..."):
        for tkr in tickers:
            df = fetch_ohlc_window(tkr, start_date, end_date)
            if df.empty:
                errors.append(f"{tkr}: no data returned (check ticker).")
                continue

            r_s = nearest_prev_trading_row(df, start_date)
            r_e = nearest_prev_trading_row(df, end_date)

            if r_s is None or r_e is None:
                errors.append(f"{tkr}: missing trading day.")
                continue

            s_high, s_low = safe_float(r_s["High"]), safe_float(r_s["Low"])
            e_high, e_low = safe_float(r_e["High"]), safe_float(r_e["Low"])

            start_mid = (s_high + s_low) / 2
            end_mid = (e_high + e_low) / 2
            pct_change = (end_mid / start_mid) - 1
            pnl = amount * pct_change

            summary_rows.append({
                "Ticker": tkr,
                "Start Date Used": r_s.name.date().isoformat(),
                "End Date Used": r_e.name.date().isoformat(),
                "Start Mid": start_mid,
                "End Mid": end_mid,
                "Percent Change": pct_change,
                "Profit / Loss ($)": pnl,
            })

            df_r = df.loc[start_date:end_date].copy()
            df_r["Series Price"] = (df_r["High"] + df_r["Low"]) / 2
            for i, r in df_r.iterrows():
                chart_rows.append({"Date": i, "Ticker": tkr, "Series Price": r["Series Price"]})

    if errors:
        st.warning(" | ".join(errors))

    summary_df = pd.DataFrame(summary_rows).sort_values("Profit / Loss ($)")

    worst = summary_df.iloc[0]
    best = summary_df.iloc[-1]

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("WORST TICKER", worst["Ticker"])
    m2.metric("WORST P/L", fmt_money(worst["Profit / Loss ($)"]))
    m3.metric("WORST %", fmt_pct(worst["Percent Change"]))
    m4.metric("BEST TICKER", best["Ticker"])
    m5.metric("BEST P/L", fmt_money(best["Profit / Loss ($)"]))
    m6.metric("BEST %", fmt_pct(best["Percent Change"]))

    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame(chart_rows)
    chart_df["Base"] = chart_df.groupby("Ticker")["Series Price"].transform("first")
    chart_df["Indexed (Start=100)"] = chart_df["Series Price"] / chart_df["Base"] * 100

    fig = px.line(chart_df, x="Date", y="Indexed (Start=100)", color="Ticker")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ff9900", family="Courier New"),
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Enter inputs above, then press ENTER.")
