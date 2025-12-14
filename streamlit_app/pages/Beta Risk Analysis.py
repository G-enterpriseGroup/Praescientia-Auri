import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
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
[data-testid="stDataFrame"] { border: 2px solid #ff9900 !important; border-radius: 0px !important; }
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

st.title("MID-PRICE DROP COMPARATOR (DAILY HI/LO MID)")
st.markdown("---")

# ----------------------------
# Helpers
# ----------------------------
def normalize_ticker_text(s: str) -> str:
    # Force uppercase and compress whitespace
    if not s:
        return ""
    return " ".join(s.upper().split())

def parse_tickers_space(raw: str) -> list[str]:
    raw = normalize_ticker_text(raw)
    if not raw:
        return []
    parts = [p for p in raw.split(" ") if p]
    # de-dup while keeping order
    seen = set()
    out = []
    for t in parts:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

@st.cache_data(ttl=60*30, show_spinner=False)
def fetch_ohlc_window(ticker: str, start_dt: date, end_dt: date) -> pd.DataFrame:
    """
    Fetch daily OHLC a bit wider than requested to allow finding nearest prior trading day.
    """
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
    df = df[keep]
    return df

def nearest_prev_trading_row(df: pd.DataFrame, target_dt: date) -> pd.Series | None:
    if df is None or df.empty:
        return None
    t = pd.to_datetime(target_dt)
    eligible = df[df.index <= t]
    if eligible.empty:
        return None
    return eligible.iloc[-1]

def fmt_money(x: float) -> str:
    if x is None or pd.isna(x):
        return "—"
    if x < 0:
        return f"(${abs(x):,.2f})"
    return f"${x:,.2f}"

def fmt_pct(x: float) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x*100:.2f}%"

# ----------------------------
# Sidebar Inputs
# ----------------------------
def on_tickers_change():
    st.session_state["tickers_text"] = normalize_ticker_text(st.session_state["tickers_text"])

with st.sidebar:
    st.header("INPUTS")

    if "tickers_text" not in st.session_state:
        st.session_state["tickers_text"] = "CLOZ SPY"

    st.text_input(
        "TICKERS (space-separated)",
        key="tickers_text",
        on_change=on_tickers_change,
        help="Example: CLOZ SPY JAAA",
    )

    amt = st.number_input("AMOUNT ($)", min_value=0.0, value=80000.0, step=1000.0)
    sd = st.date_input("START DATE", value=date(2025, 2, 24))
    ed = st.date_input("END DATE", value=date(2025, 4, 7))

    st.markdown("---")
    st.caption("Daily Mid Price = (High + Low) / 2")
    run = st.button("RUN COMPARISON")

# ----------------------------
# Main
# ----------------------------
tickers = parse_tickers_space(st.session_state.get("tickers_text", ""))

if run:
    if not tickers:
        st.error("Enter at least one ticker (space-separated).")
        st.stop()

    if ed < sd:
        st.error("End Date must be on/after Start Date.")
        st.stop()

    results = []
    errors = []

    # For chart: build a combined dataframe of mid prices for each ticker over the requested range
    mid_panel = pd.DataFrame()

    with st.spinner("Pulling daily High/Low data..."):
        for tkr in tickers:
            df = fetch_ohlc_window(tkr, sd, ed)
            if df.empty:
                errors.append(f"{tkr}: no data returned (check ticker).")
                continue

            r_s = nearest_prev_trading_row(df, sd)
            r_e = nearest_prev_trading_row(df, ed)

            if r_s is None:
                errors.append(f"{tkr}: no trading day found on/before Start Date.")
                continue
            if r_e is None:
                errors.append(f"{tkr}: no trading day found on/before End Date.")
                continue

            sd_used = pd.to_datetime(r_s.name).date()
            ed_used = pd.to_datetime(r_e.name).date()

            s_hi, s_lo = float(r_s["High"]), float(r_s["Low"])
            e_hi, e_lo = float(r_e["High"]), float(r_e["Low"])

            s_mid = (s_hi + s_lo) / 2.0
            e_mid = (e_hi + e_lo) / 2.0

            chg = (e_mid / s_mid) - 1.0 if s_mid != 0 else None
            pnl = amt * chg if chg is not None else None

            results.append({
                "Ticker": tkr,
                "Start Date Used": sd_used.isoformat(),
                "End Date Used": ed_used.isoformat(),
                "Start High": s_hi,
                "Start Low": s_lo,
                "Start Mid Price": s_mid,
                "End High": e_hi,
                "End Low": e_lo,
                "End Mid Price": e_mid,
                "Percent Change": chg,
                "Profit/Loss ($)": pnl,
            })

            # Build series for chart for the actual requested window (use trading days in that window)
            w = df.copy()
            w["Mid Price"] = (w["High"] + w["Low"]) / 2.0
            w = w[(w.index >= pd.to_datetime(sd)) & (w.index <= pd.to_datetime(ed))]
            if not w.empty:
                mid_panel[tkr] = w["Mid Price"]

    if errors:
        st.warning("SOME TICKERS HAD ISSUES:\n\n- " + "\n- ".join(errors))

    if not results:
        st.error("No results to display.")
        st.stop()

    out = pd.DataFrame(results).sort_values(by="Profit/Loss ($)", ascending=True).reset_index(drop=True)

    worst = out.iloc[0]
    best = out.iloc[-1]

    c1, c2, c3 = st.columns(3)
    c1.metric("WORST LOSS TICKER", str(worst["Ticker"]))
    c2.metric("WORST P/L", fmt_money(float(worst["Profit/Loss ($)"])))
    c3.metric("WORST %", fmt_pct(float(worst["Percent Change"])))

    st.markdown("---")

    # Display table (formatted)
    show = out.copy()
    for col in ["Start High", "Start Low", "Start Mid Price", "End High", "End Low", "End Mid Price"]:
        show[col] = show[col].map(lambda x: f"{float(x):,.2f}")
    show["Percent Change"] = show["Percent Change"].map(lambda x: fmt_pct(float(x)))
    show["Profit/Loss ($)"] = show["Profit/Loss ($)"].map(lambda x: fmt_money(float(x)))

    st.subheader("RESULTS (RANKED BY WORST LOSS)")
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Line chart of mid prices
    st.subheader("VISUAL: DAILY MID PRICE (HI/LO MID)")

    if mid_panel.empty:
        st.info("No chart data available for the selected date window (check dates/tickers).")
    else:
        fig = plt.figure()
        ax = fig.add_subplot(111)

        # Plot each ticker series
        for col in mid_panel.columns:
            ax.plot(mid_panel.index, mid_panel[col], label=col)

        ax.set_xlabel("Date")
        ax.set_ylabel("Mid Price ((High+Low)/2)")
        ax.legend()
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)

        st.pyplot(fig)

    st.markdown("---")
    st.subheader("QUICK READ")
    st.write(
        f"- Worst loss: **{worst['Ticker']}** at **{fmt_money(float(worst['Profit/Loss ($)']))}** "
        f"from {worst['Start Date Used']} → {worst['End Date Used']} (mid-price)."
    )
    st.write(
        f"- Best (least loss / most gain): **{best['Ticker']}** at **{fmt_money(float(best['Profit/Loss ($)']))}** "
        f"from {best['Start Date Used']} → {best['End Date Used']} (mid-price)."
    )

else:
    st.info("Enter inputs in the left sidebar, then click **RUN COMPARISON**.")
