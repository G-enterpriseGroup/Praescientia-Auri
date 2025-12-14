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

st.title("MID-PRICE DROP COMPARATOR (DAILY MID = (HIGH + LOW) / 2)")
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
        threads=True,
    )
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    keep = [c for c in ["High", "Low", "Open", "Close", "Volume"] if c in df.columns]
    return df[keep]

def nearest_prev_trading_row(df: pd.DataFrame, target_dt: date):
    t = pd.to_datetime(target_dt)
    eligible = df[df.index <= t]
    if eligible.empty:
        return None
    return eligible.iloc[-1]

def fmt_money(x):
    if x is None or pd.isna(x):
        return "—"
    return f"(${abs(x):,.2f})" if x < 0 else f"${x:,.2f}"

def fmt_pct(x):
    if x is None or pd.isna(x):
        return "—"
    return f"{x*100:.2f}%"

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None

# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.header("INPUTS")
    raw_tickers = st.text_input("TICKERS (space-separated)", value="CLOZ SPY")
    amount = st.number_input("AMOUNT ($)", min_value=0.0, value=80000.0, step=1000.0)
    start_date = st.date_input("START DATE", value=date(2025, 2, 24))
    end_date = st.date_input("END DATE", value=date(2025, 4, 7))
    st.markdown("---")
    st.caption("Daily Mid Price = (High + Low) / 2")
    run = st.button("RUN COMPARISON")

tickers = parse_tickers_space(raw_tickers)

# ----------------------------
# Main
# ------------
