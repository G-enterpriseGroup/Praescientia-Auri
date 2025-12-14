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
    # split on whitespace, uppercase, de-dup keep order
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
    """
    Fetch daily OHLC for a window around requested dates to allow:
    - nearest previous trading day for start/end
    - mid-price series for chart over the full range
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

    # Keep only needed columns
    keep = [c for c in ["High", "Low", "Open", "Close", "Volume"] if c in df.columns]
    return df[keep]

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

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None

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
    st.caption("Daily Mid Price = (High + Low) / 2")
    run = st.button("RUN COMPARISON")

tickers = parse_tickers_space(raw_tickers)

# ----------------------------
# Main
# ----------------------------
if run:
    if not tickers:
        st.error("Enter at least one ticker (space-separated). Example: CLOZ SPY")
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

            # nearest previous trading rows for selected start/end
            r_s = nearest_prev_trading_row(df, start_date)
            r_e = nearest_prev_trading_row(df, end_date)

            if r_s is None:
                errors.append(f"{tkr}: no trading day found on/before start date.")
                continue
            if r_e is None:
                errors.append(f"{tkr}: no trading day found on/before end date.")
                continue

            used_start = pd.to_datetime(r_s.name).date()
            used_end = pd.to_datetime(r_e.name).date()

            s_high, s_low = safe_float(r_s.get("High")), safe_float(r_s.get("Low"))
            e_high, e_low = safe_float(r_e.get("High")), safe_float(r_e.get("Low"))

            if s_high is None or s_low is None or e_high is None or e_low is None:
                errors.append(f"{tkr}: missing High/Low data in range.")
                continue

            start_mid = (s_high + s_low) / 2.0
            end_mid = (e_high + e_low) / 2.0

            pct_change = (end_mid / start_mid) - 1.0 if start_mid != 0 else None
            pnl = amount * pct_change if pct_change is not None else None

            summary_rows.append({
                "Ticker": tkr,
                "Start Date Used": used_start.isoformat(),
                "End Date Used": used_end.isoformat(),
                "Start High": s_high,
                "Start Low": s_low,
                "Start Mid": start_mid,
                "End High": e_high,
                "End Low": e_low,
                "End Mid": end_mid,
                "Percent Change": pct_change,
                "Profit / Loss ($)": pnl,
            })

            # Build chart series over the actual requested date range (use trading days in range)
            df_range = df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))].copy()
            if not df_range.empty and "High" in df_range.columns and "Low" in df_range.columns:
                df_range["Mid Price"] = (df_range["High"].astype(float) + df_range["Low"].astype(float)) / 2.0
                for dt_idx, row in df_range.iterrows():
                    chart_rows.append({
                        "Date": dt_idx,
                        "Ticker": tkr,
                        "Mid Price": float(row["Mid Price"]),
                    })

    if errors:
        st.warning("SOME TICKERS HAD ISSUES:\n\n- " + "\n- ".join(errors))

    if not summary_rows:
        st.error("No results to display.")
        st.stop()

    summary_df = pd.DataFrame(summary_rows)

    # Rank by worst loss (most negative P/L)
    summary_df = summary_df.sort_values(by="Profit / Loss ($)", ascending=True).reset_index(drop=True)

    worst = summary_df.iloc[0]
    best = summary_df.iloc[-1]

    c1, c2, c3 = st.columns(3)
    c1.metric("WORST TICKER", worst["Ticker"])
    c2.metric("WORST P/L", fmt_money(float(worst["Profit / Loss ($)"])))
    c3.metric("WORST %", fmt_pct(float(worst["Percent Change"])))

    st.markdown("---")

    # Display table (pretty formatting)
    display_df = summary_df.copy()
    money_cols = ["Start High", "Start Low", "Start Mid", "End High", "End Low", "End Mid"]
    for c in money_cols:
        display_df[c] = display_df[c].map(lambda x: f"{float(x):,.2f}")

    display_df["Percent Change"] = display_df["Percent Change"].map(lambda x: fmt_pct(float(x)))
    display_df["Profit / Loss ($)"] = display_df["Profit / Loss ($)"].map(lambda x: fmt_money(float(x)))

    st.subheader("RESULTS (RANKED BY WORST LOSS)")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("VISUAL: DAILY MID PRICE LINES (HIGH/LOW MID)")

    if chart_rows:
        chart_df = pd.DataFrame(chart_rows).sort_values(["Date", "Ticker"])
        fig = px.line(
            chart_df,
            x="Date",
            y="Mid Price",
            color="Ticker",
            title="Mid Price Over Time (Mid = (High + Low) / 2)"
        )
        # Make plot match the theme (no fixed colors; just dark background & orange text)
        fig.update_layout(
            paper_bgcolor="black",
            plot_bgcolor="black",
            font=dict(color="#ff9900", family="Courier New"),
            legend=dict(font=dict(color="#ff9900")),
            xaxis=dict(gridcolor="#222222", zerolinecolor="#222222"),
            yaxis=dict(gridcolor="#222222", zerolinecolor="#222222"),
            title=dict(font=dict(color="#ff9900")),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough range data to draw lines (try a wider date range).")

    st.markdown("---")
    st.subheader("QUICK READ")
    st.write(
        f"- Worst loss: **{worst['Ticker']}** at **{fmt_money(float(worst['Profit / Loss ($)']))}** "
        f"from {worst['Start Date Used']} → {worst['End Date Used']}."
    )
    st.write(
        f"- Best (least loss / most gain): **{best['Ticker']}** at **{fmt_money(float(best['Profit / Loss ($)']))}** "
        f"from {best['Start Date Used']} → {best['End Date Used']}."
    )

else:
    st.info("Enter inputs in the left sidebar, then click **RUN COMPARISON**.")
