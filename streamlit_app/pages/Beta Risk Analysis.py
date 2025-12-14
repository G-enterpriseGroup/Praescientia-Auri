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
}

input, textarea {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}

div[data-baseweb="input"] > div {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
}

.stButton > button {
  background: #000000 !important;
  color: #ff9900 !important;
  border: 3px solid #ff9900 !important;
  border-radius: 0px !important;
  font-family: "Courier New", Courier, monospace !important;
  text-transform: uppercase;
}
.stButton > button:hover { background: #111111 !important; }

[data-testid="stDataFrame"] {
  border: 2px solid #ff9900 !important;
}

div[data-testid="stMetric"] {
  border: 2px solid #ff9900;
  padding: 10px;
  background: #050505;
}

section[data-testid="stSidebar"] { display: none !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.title("MID-PRICE DROP COMPARATOR")
st.caption("Loss math uses Mid = (High + Low) / 2 • Chart normalized to start at 100")
st.markdown("---")

# ----------------------------
# Helpers
# ----------------------------
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

# ----------------------------
# INPUTS (ON PAGE)
# ----------------------------
st.subheader("INPUTS")

c1, c2, c3, c4 = st.columns([2.2, 1.6, 1.3, 1.3])

with c1:
    raw_tickers = st.text_input("TICKERS (space-separated)", value="CLOZ SPY")

with c2:
    amount = st.number_input(
        "AMOUNT ($)",
        min_value=0.0,
        value=80000.0,
        step=1000.0
    )
    st.caption(f"Using: ${amount:,.2f}")

with c3:
    start_date = st.date_input("START DATE", value=date(2025, 2, 24))

with c4:
    end_date = st.date_input("END DATE", value=date(2025, 4, 7))

run = st.button("RUN COMPARISON")

tickers = parse_tickers_space(raw_tickers)

# ----------------------------
# MAIN
# ----------------------------
if run:
    if not tickers or end_date < start_date:
        st.error("Invalid inputs.")
        st.stop()

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
            "Start Date Used": rs.name.date(),
            "End Date Used": re.name.date(),
            "Start Mid": start_mid,
            "End Mid": end_mid,
            "Percent Change": pct_change,
            "Profit / Loss ($)": pnl,
        })

        df_range = df.loc[start_date:end_date].copy()
        df_range["Series"] = (df_range["High"] + df_range["Low"]) / 2
        for idx, row in df_range.iterrows():
            chart_data.append({
                "Date": idx,
                "Ticker": tkr,
                "Series": row["Series"]
            })

    if not summary:
        st.error("No data returned.")
        st.stop()

    df_sum = pd.DataFrame(summary).sort_values("Profit / Loss ($)").reset_index(drop=True)

    worst = df_sum.iloc[0]
    best = df_sum.iloc[-1]

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("WORST TICKER", worst["Ticker"])
    m2.metric("WORST P/L", fmt_money(worst["Profit / Loss ($)"]))
    m3.metric("WORST %", fmt_pct(worst["Percent Change"]))
    m4.metric("BEST TICKER", best["Ticker"])
    m5.metric("BEST P/L", fmt_money(best["Profit / Loss ($)"]))
    m6.metric("BEST %", fmt_pct(best["Percent Change"]))

    st.markdown("---")

    display = df_sum.copy()
    display["Start Mid"] = display["Start Mid"].map(lambda x: f"{x:,.2f}")
    display["End Mid"] = display["End Mid"].map(lambda x: f"{x:,.2f}")
    display["Percent Change"] = display["Percent Change"].map(fmt_pct)
    display["Profit / Loss ($)"] = display["Profit / Loss ($)"].map(fmt_money)

    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("NORMALIZED PERFORMANCE (START = 100)")

    chart_df = pd.DataFrame(chart_data)
    chart_df["Base"] = chart_df.groupby("Ticker")["Series"].transform("first")
    chart_df["Indexed"] = (chart_df["Series"] / chart_df["Base"]) * 100

    fig = px.line(
        chart_df,
        x="Date",
        y="Indexed",
        color="Ticker",
        title="Normalized Performance"
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ff9900", family="Courier New"),
        xaxis=dict(gridcolor="rgba(255,153,0,0.2)"),
        yaxis=dict(gridcolor="rgba(255,153,0,0.2)"),
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Enter inputs above and click RUN COMPARISON.")
