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

div[data-baseweb="select"] > div,
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

[data-testid="stDataFrame"] {
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}

section[data-testid="stSidebar"] {
  background: #000000 !important;
  border-right: 2px solid #ff9900 !important;
}
section[data-testid="stSidebar"] * {
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
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
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.title("MID-PRICE DROP COMPARATOR (CALC = MID, CHART = CLOSE)")
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

@st.cache_data(ttl=60*30, show_spinner=False)
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
    t = pd.to_datetime(target_dt)
    eligible = df[df.index <= t]
    if eligible.empty:
        return None
    return eligible.iloc[-1]

def fmt_money(x):
    if x < 0:
        return f"(${abs(x):,.2f})"
    return f"${x:,.2f}"

def fmt_pct(x):
    return f"{x*100:.2f}%"

# ----------------------------
# Sidebar Inputs
# ----------------------------
with st.sidebar:
    st.header("INPUTS")
    raw_tickers = st.text_input("TICKERS (space-separated)", value="CLOZ SPY")
    amount = st.number_input("AMOUNT ($)", min_value=0.0, value=80000.0, step=1000.0)
    start_date = st.date_input("START DATE", value=date(2025, 2, 24))
    end_date = st.date_input("END DATE", value=date(2025, 4, 7))
    st.markdown("---")
    run = st.button("RUN COMPARISON")

tickers = parse_tickers_space(raw_tickers)

# ----------------------------
# Main
# ----------------------------
if run:
    summary_rows = []
    chart_rows = []

    for tkr in tickers:
        df = fetch_ohlc_window(tkr, start_date, end_date)
        if df.empty:
            continue

        r_s = nearest_prev_trading_row(df, start_date)
        r_e = nearest_prev_trading_row(df, end_date)
        if r_s is None or r_e is None:
            continue

        s_mid = (r_s["High"] + r_s["Low"]) / 2
        e_mid = (r_e["High"] + r_e["Low"]) / 2

        pct_change = (e_mid / s_mid) - 1
        pnl = amount * pct_change

        summary_rows.append({
            "Ticker": tkr,
            "Start Date Used": r_s.name.date().isoformat(),
            "End Date Used": r_e.name.date().isoformat(),
            "Start Mid": s_mid,
            "End Mid": e_mid,
            "Percent Change": pct_change,
            "Profit / Loss ($)": pnl,
        })

        # ---- ONLY CHANGE IS HERE: chart uses CLOSE ----
        df_range = df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))]
        for dt, row in df_range.iterrows():
            chart_rows.append({
                "Date": dt,
                "Ticker": tkr,
                "Close Price": float(row["Close"]),
            })

    summary_df = pd.DataFrame(summary_rows).sort_values("Profit / Loss ($)")

    worst = summary_df.iloc[0]
    best = summary_df.iloc[-1]

    c1, c2, c3 = st.columns(3)
    c1.metric("WORST TICKER", worst["Ticker"])
    c2.metric("WORST P/L", fmt_money(worst["Profit / Loss ($)"]))
    c3.metric("WORST %", fmt_pct(worst["Percent Change"]))

    st.markdown("---")

    display_df = summary_df.copy()
    display_df["Start Mid"] = display_df["Start Mid"].map(lambda x: f"{x:,.2f}")
    display_df["End Mid"] = display_df["End Mid"].map(lambda x: f"{x:,.2f}")
    display_df["Percent Change"] = display_df["Percent Change"].map(fmt_pct)
    display_df["Profit / Loss ($)"] = display_df["Profit / Loss ($)"].map(fmt_money)

    st.subheader("RESULTS (RANKED BY WORST LOSS)")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("VISUAL: DAILY CLOSE PRICE")

    chart_df = pd.DataFrame(chart_rows)
    fig = px.line(
        chart_df,
        x="Date",
        y="Close Price",
        color="Ticker",
        title="Daily Close Price (Visual Only)",
    )

    fig.update_layout(
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="#ff9900", family="Courier New"),
        legend=dict(font=dict(color="#ff9900")),
        xaxis=dict(gridcolor="#222222"),
        yaxis=dict(gridcolor="#222222"),
    )

    st.plotly_chart(fig, use_container_width=True)
