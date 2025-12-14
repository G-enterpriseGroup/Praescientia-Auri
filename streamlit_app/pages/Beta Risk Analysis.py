import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta

# ============================
# PAGE + THEME (90s ORANGE)
# ============================
st.set_page_config(page_title="Mid-Price Drop Comparator", layout="wide")

CSS = """
<style>
html, body, [class*="css"] {
  background-color: #000000 !important;
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}

.block-container {
  padding-top: 1rem;
  padding-bottom: 1rem;
}

h1, h2, h3, h4 {
  color: #ff9900 !important;
}

input, textarea {
  background-color: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}

.stButton > button {
  background-color: #000000 !important;
  color: #ff9900 !important;
  border: 3px solid #ff9900 !important;
  border-radius: 0px !important;
  font-family: "Courier New", Courier, monospace !important;
  text-transform: uppercase;
}

.stButton > button:hover {
  background-color: #111111 !important;
}

[data-testid="stDataFrame"] {
  border: 2px solid #ff9900 !important;
}

section[data-testid="stSidebar"] {
  background-color: #000000 !important;
  border-right: 2px solid #ff9900 !important;
}

div[data-testid="stMetric"] {
  border: 2px solid #ff9900;
  padding: 10px;
  background-color: #050505;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.title("MID-PRICE DROP COMPARATOR")
st.caption("Loss math uses Mid = (High + Low) / 2 • Chart uses Daily Close")
st.markdown("---")

# ============================
# HELPERS
# ============================
def parse_tickers_space(raw: str):
    return list(dict.fromkeys([t.upper() for t in raw.split() if t.strip()]))

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_ohlc(ticker, start_dt, end_dt):
    s = datetime.combine(start_dt, datetime.min.time()) - timedelta(days=10)
    e = datetime.combine(end_dt, datetime.min.time()) + timedelta(days=1)
    df = yf.download(
        ticker,
        start=s.strftime("%Y-%m-%d"),
        end=e.strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=False,
        progress=False,
    )
    if df.empty:
        return df
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df

def nearest_prev_row(df, target_date):
    eligible = df[df.index <= pd.to_datetime(target_date)]
    if eligible.empty:
        return None
    return eligible.iloc[-1]

def fmt_money(x):
    return f"(${abs(x):,.2f})" if x < 0 else f"${x:,.2f}"

def fmt_pct(x):
    return f"{x*100:.2f}%"

# ============================
# SIDEBAR INPUTS
# ============================
with st.sidebar:
    st.header("INPUTS")
    raw_tickers = st.text_input("TICKERS (space-separated)", value="CLOZ SPY")
    amount = st.number_input("AMOUNT ($)", value=80000.0, step=1000.0)
    start_date = st.date_input("START DATE", value=date(2025, 2, 24))
    end_date = st.date_input("END DATE", value=date(2025, 4, 7))
    run = st.button("RUN COMPARISON")

tickers = parse_tickers_space(raw_tickers)

# ============================
# MAIN LOGIC
# ============================
if run:
    if not tickers or end_date < start_date:
        st.error("Invalid inputs.")
        st.stop()

    st.write(f"**Tickers:** {' '.join(tickers)}")

    summary = []
    chart_data = []

    for tkr in tickers:
        df = fetch_ohlc(tkr, start_date, end_date)
        if df.empty:
            continue

        rs = nearest_prev_row(df, start_date)
        re = nearest_prev_row(df, end_date)
        if rs is None or re is None:
            continue

        start_mid = (rs["High"] + rs["Low"]) / 2
        end_mid = (re["High"] + re["Low"]) / 2
        pct_change = (end_mid / start_mid) - 1
        pnl = amount * pct_change

        summary.append({
            "Ticker": tkr,
            "Start Date Used": rs.name.date().isoformat(),
            "End Date Used": re.name.date().isoformat(),
            "Start High": rs["High"],
            "Start Low": rs["Low"],
            "Start Mid Price": start_mid,
            "End High": re["High"],
            "End Low": re["Low"],
            "End Mid Price": end_mid,
            "Percent Change": pct_change,
            "Profit / Loss ($)": pnl,
        })

        df_range = df.loc[start_date:end_date].copy()
        if "Close" in df_range.columns:
            for idx, row in df_range.iterrows():
                chart_data.append({
                    "Date": idx,
                    "Ticker": tkr,
                    "Close Price": float(row["Close"])
                })

    if not summary:
        st.error("No data returned.")
        st.stop()

    df_summary = pd.DataFrame(summary).sort_values("Profit / Loss ($)").reset_index(drop=True)

    worst = df_summary.iloc[0]
    best = df_summary.iloc[-1]

    c1, c2, c3 = st.columns(3)
    c1.metric("WORST TICKER", worst["Ticker"])
    c2.metric("WORST LOSS", fmt_money(worst["Profit / Loss ($)"]))
    c3.metric("WORST %", fmt_pct(worst["Percent Change"]))

    st.markdown("---")
    st.subheader("RESULTS (RANKED BY WORST LOSS)")

    display = df_summary.copy()
    price_cols = [
        "Start High", "Start Low", "Start Mid Price",
        "End High", "End Low", "End Mid Price"
    ]
    for c in price_cols:
        display[c] = display[c].map(lambda x: f"{x:,.2f}")
    display["Percent Change"] = display["Percent Change"].map(fmt_pct)
    display["Profit / Loss ($)"] = display["Profit / Loss ($)"].map(fmt_money)

    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("VISUAL — DAILY CLOSE PRICES")

    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        fig = px.line(
            df_chart,
            x="Date",
            y="Close Price",
            color="Ticker",
            title="Daily Clo
