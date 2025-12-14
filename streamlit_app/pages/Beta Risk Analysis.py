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
    seen, out = set(), []
    for t in parts:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

@st.cache_data(ttl=1800, show_spinner=False)
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
# INPUT FORM (ENTER SUBMITS)
# ----------------------------
st.subheader("INPUTS")

with st.form("run_form", clear_on_submit=False):
    c1, c2, c3, c4 = st.columns([2.2, 1.3, 1.3, 1.2])

    with c1:
        raw_tickers = st.text_input("TICKERS (space-separated)", value="CLOZ SPY")
    with c2:
        amount = st.number_input("AMOUNT ($)", min_value=0.0, value=80000.0, step=1000.0)
    with c3:
        start_date = st.date_input("START DATE", value=date(2025, 2, 24))
    with c4:
        end_date = st.date_input("END DATE", value=date(2025, 4, 7))

    run = st.form_submit_button("RUN COMPARISON")

tickers = parse_tickers_space(raw_tickers)

# ----------------------------
# MAIN
# ----------------------------
if run:
    if not tickers:
        st.error("Enter at least one ticker.")
        st.stop()

    if end_date < start_date:
        st.error("End Date must be on/after Start Date.")
        st.stop()

    summary_rows, chart_rows, errors = [], [], []

    for tkr in tickers:
        df = fetch_ohlc_window(tkr, start_date, end_date)
        if df.empty:
            errors.append(f"{tkr}: no data.")
            continue

        rs = nearest_prev_trading_row(df, start_date)
        re = nearest_prev_trading_row(df, end_date)
        if rs is None or re is None:
            errors.append(f"{tkr}: missing trading dates.")
            continue

        s_mid = (rs["High"] + rs["Low"]) / 2
        e_mid = (re["High"] + re["Low"]) / 2
        pct = (e_mid / s_mid) - 1
        pnl = amount * pct

        summary_rows.append({
            "Ticker": tkr,
            "Start Date Used": rs.name.date().isoformat(),
            "End Date Used": re.name.date().isoformat(),
            "Start Mid": s_mid,
            "End Mid": e_mid,
            "Percent Change": pct,
            "Profit / Loss ($)": pnl
        })

        df_r = df.loc[start_date:end_date].copy()
        df_r["Mid"] = (df_r["High"] + df_r["Low"]) / 2
        for i, r in df_r.iterrows():
            chart_rows.append({"Date": i, "Ticker": tkr, "Price": r["Mid"]})

    if errors:
        st.warning("\n".join(errors))

    df_sum = pd.DataFrame(summary_rows).sort_values("Profit / Loss ($)")
    worst, best = df_sum.iloc[0], df_sum.iloc[-1]

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("WORST", worst["Ticker"])
    m2.metric("WORST P/L", fmt_money(worst["Profit / Loss ($)"]))
    m3.metric("WORST %", fmt_pct(worst["Percent Change"]))
    m4.metric("BEST", best["Ticker"])
    m5.metric("BEST P/L", fmt_money(best["Profit / Loss ($)"]))
    m6.metric("BEST %", fmt_pct(best["Percent Change"]))

    st.dataframe(df_sum, use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame(chart_rows)
    chart_df["Base"] = chart_df.groupby("Ticker")["Price"].transform("first")
    chart_df["Indexed"] = chart_df["Price"] / chart_df["Base"] * 100

    fig = px.line(chart_df, x="Date", y="Indexed", color="Ticker")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ff9900", family="Courier New"),
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Enter inputs above and press ENTER.")
