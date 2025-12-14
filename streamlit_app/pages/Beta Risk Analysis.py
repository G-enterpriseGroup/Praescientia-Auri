import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime, timedelta

# ----------------------------
# Page Config + Theme
# ----------------------------
st.set_page_config(page_title="Mid-Price Stress Comparator", layout="wide")

CSS = """
<style>
html, body, [class*="css"]  {
  background: #000000 !important;
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}
section[data-testid="stSidebar"] {
  background: #000000 !important;
  border-right: 2px solid #ff9900 !important;
}
section[data-testid="stSidebar"] * {
  color: #ff9900 !important;
}
.stButton > button {
  background: #000000 !important;
  color: #ff9900 !important;
  border: 3px solid #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.title("MID-PRICE STRESS TEST (HI/LO MID)")
st.markdown("---")

# ----------------------------
# Helpers
# ----------------------------
def normalize_tickers(txt):
    return " ".join(txt.upper().split())

def parse_tickers(txt):
    return list(dict.fromkeys(txt.split()))

@st.cache_data(ttl=1800)
def fetch_data(ticker, sd, ed):
    s = datetime.combine(sd, datetime.min.time()) - timedelta(days=10)
    e = datetime.combine(ed, datetime.min.time()) + timedelta(days=1)
    df = yf.download(ticker, start=s, end=e, progress=False)
    if df.empty:
        return df
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df["Mid"] = (df["High"] + df["Low"]) / 2
    return df

def nearest(df, d):
    df = df[df.index <= pd.to_datetime(d)]
    return df.iloc[-1] if not df.empty else None

# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.header("INPUTS")
    tickers_txt = st.text_input(
        "TICKERS (space separated)",
        value="CLOZ SPY",
        on_change=lambda: st.session_state.update(
            {"tickers_txt": normalize_tickers(st.session_state["tickers_txt"])}
        ),
        key="tickers_txt"
    )
    amount = st.number_input("INVESTMENT AMOUNT ($)", value=80000.0, step=1000.0)
    sd = st.date_input("START DATE", value=date(2025, 2, 24))
    ed = st.date_input("END DATE", value=date(2025, 4, 7))
    run = st.button("RUN ANALYSIS")

tickers = parse_tickers(normalize_tickers(tickers_txt))

# ----------------------------
# Main
# ----------------------------
if run:
    panel = pd.DataFrame()
    summary = []

    for t in tickers:
        df = fetch_data(t, sd, ed)
        if df.empty:
            continue

        rs = nearest(df, sd)
        re = nearest(df, ed)

        s_mid = rs["Mid"]
        e_mid = re["Mid"]

        pct = (e_mid / s_mid) - 1
        pnl = pct * amount

        summary.append({
            "Ticker": t,
            "Start Mid": s_mid,
            "End Mid": e_mid,
            "Percent Change": pct,
            "Profit/Loss ($)": pnl
        })

        w = df[(df.index >= sd) & (df.index <= ed)].copy()
        w["Normalized"] = (w["Mid"] / s_mid) * 100
        w["PnL Curve"] = (w["Normalized"] / 100 - 1) * amount
        panel[(t, "Norm")] = w["Normalized"]
        panel[(t, "PnL")] = w["PnL Curve"]

    if not summary:
        st.error("No valid data.")
        st.stop()

    panel.columns = pd.MultiIndex.from_tuples(panel.columns)
    summary_df = pd.DataFrame(summary).sort_values("Profit/Loss ($)")

    st.subheader("SUMMARY (WORST LOSS FIRST)")
    st.dataframe(summary_df, use_container_width=True)

    # ----------------------------
    # ADVANCED MATPLOTLIB CHART
    # ----------------------------
    st.subheader("ADVANCED VISUAL — NORMALIZED DROP & $ IMPACT")

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 9), sharex=True, dpi=140,
        gridspec_kw={"height_ratios": [2, 1]}
    )

    fig.patch.set_facecolor("black")
    for ax in (ax1, ax2):
        ax.set_facecolor("black")
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.tick_params(colors="#ff9900")
        for spine in ax.spines.values():
            spine.set_color("#ff9900")

    # --- Top: Normalized Price ---
    for t in tickers:
        ax1.plot(panel.index, panel[(t, "Norm")], linewidth=2.2, label=t)
        ax1.fill_between(
            panel.index, panel[(t, "Norm")], 100,
            alpha=0.15
        )

    ax1.axhline(100, color="white", linestyle=":", alpha=0.6)
    ax1.set_ylabel("Normalized Mid Price (Start = 100)", color="#ff9900")
    ax1.legend(loc="upper left", frameon=False)

    # --- Bottom: P/L ---
    for t in tickers:
        ax2.plot(panel.index, panel[(t, "PnL")], linewidth=2)

    ax2.axhline(0, color="white", linestyle=":")
    ax2.set_ylabel("Dollar P/L ($)", color="#ff9900")
    ax2.set_xlabel("Date", color="#ff9900")

    # Vertical markers
    ax2.axvline(pd.to_datetime(sd), linestyle="--", alpha=0.5)
    ax2.axvline(pd.to_datetime(ed), linestyle="--", alpha=0.5)

    plt.tight_layout()
    st.pyplot(fig)

    worst = summary_df.iloc[0]
    st.markdown("---")
    st.markdown(
        f"**Worst drawdown:** `{worst['Ticker']}` → "
        f"**${worst['Profit/Loss ($)']:,.2f}**"
    )

else:
    st.info("Enter inputs and click RUN ANALYSIS.")
