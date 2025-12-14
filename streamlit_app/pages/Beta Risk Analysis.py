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

div[data-baseweb="input"] > div {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}

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

def uppercase_tickers():
    st.session_state["raw_tickers"] = st.session_state["raw_tickers"].upper()

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
    return df[["High", "Low", "Open", "Close", "Volume"]]

def nearest_prev_trading_row(df: pd.DataFrame, target_dt: date):
    eligible = df[df.index <= pd.to_datetime(target_dt)]
    return None if eligible.empty else eligible.iloc[-1]

def fmt_money(x):
    if x is None or pd.isna(x): return "—"
    return f"(${abs(x):,.2f})" if x < 0 else f"${x:,.2f}"

def fmt_pct(x):
    if x is None or pd.isna(x): return "—"
    return f"{x * 100:.2f}%"

# ----------------------------
# INPUTS (ENTER RUNS)
# ----------------------------
st.subheader("INPUTS")

with st.form("run_form", clear_on_submit=False):
    c1, c2, c3, c4 = st.columns([2.2, 1.3, 1.3, 1.2])

    with c1:
        raw_tickers = st.text_input(
            "TICKERS (space-separated)",
            value="CLOZ SPY",
            key="raw_tickers",
            on_change=uppercase_tickers
        )

    with c2:
        amount = st.number_input(
            "AMOUNT ($)",
            min_value=0.0,
            value=80000.0,
            step=1000.0
        )

    with c3:
        start_date = st.date_input("START DATE", value=date(2025, 2, 24))
    with c4:
        end_date = st.date_input("END DATE", value=date(2025, 4, 7))

    st.markdown("")
    run = st.form_submit_button("RUN COMPARISON")

tickers = parse_tickers_space(raw_tickers)

# ----------------------------
# Main
# ----------------------------
if run:
    if not tickers:
        st.error("Enter at least one ticker.")
        st.stop()

    if end_date < start_date:
        st.error("End Date must be on/after Start Date.")
        st.stop()

    summary_rows = []
    chart_rows = []

    for tkr in tickers:
        df = fetch_ohlc_window(tkr, start_date, end_date)
        r_s = nearest_prev_trading_row(df, start_date)
        r_e = nearest_prev_trading_row(df, end_date)

        start_mid = (r_s["High"] + r_s["Low"]) / 2
        end_mid = (r_e["High"] + r_e["Low"]) / 2
        pct_change = (end_mid / start_mid) - 1
        pnl = amount * pct_change

        summary_rows.append({
            "Ticker": tkr,
            "Percent Change": pct_change,
            "Profit / Loss ($)": pnl,
        })

        df_r = df.loc[start_date:end_date]
        df_r["Series Price"] = (df_r["High"] + df_r["Low"]) / 2
        for i, r in df_r.iterrows():
            chart_rows.append({"Date": i, "Ticker": tkr, "Series Price": r["Series Price"]})

    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame(chart_rows)
    chart_df["Base"] = chart_df.groupby("Ticker")["Series Price"].transform("first")
    chart_df["Indexed (Start=100)"] = chart_df["Series Price"] / chart_df["Base"] * 100

    fig = px.line(chart_df, x="Date", y="Indexed (Start=100)", color="Ticker")
    fig.update_layout(font=dict(color="#ff9900", family="Courier New"))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Enter inputs above, then press ENTER.")
