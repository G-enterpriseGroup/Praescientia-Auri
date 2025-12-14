import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, datetime, timedelta

# ----------------------------
# Page + Theme (90s Orange)
# ----------------------------
st.set_page_config(page_title="Mid-Price Drop Comparator", layout="wide")

CSS = """
<style>
/* Overall page */
html, body, [class*="css"]  {
  background: #000000 !important;
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}

/* Remove Streamlit default padding a bit */
.block-container {
  padding-top: 1.0rem;
  padding-bottom: 1.0rem;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
  letter-spacing: 0.5px;
}

/* Inputs */
input, textarea {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
  box-shadow: none !important;
}

/* Selects / date input container */
div[data-baseweb="select"] > div,
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
.stButton > button:hover {
  background: #111111 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: #000000 !important;
  border-right: 2px solid #ff9900 !important;
}
section[data-testid="stSidebar"] * {
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}

/* Horizontal rule */
hr {
  border: 0;
  border-top: 2px dashed #ff9900;
}

/* Links */
a { color: #ffcc66 !important; }
a:hover { color: #ffffff !important; }

/* Metric cards (simple boxed look) */
div[data-testid="stMetric"] {
  border: 2px solid #ff9900;
  padding: 10px;
  border-radius: 0px;
  background: #050505;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.title("MID-PRICE DROP COMPARATOR (HI/LO MID)")
st.markdown("---")

# ----------------------------
# Helpers
# ----------------------------
def parse_tickers(raw: str) -> list[str]:
    if not raw:
        return []
    # User preference: comma-separated, no spaces. We'll still sanitize.
    parts = [p.strip().upper() for p in raw.split(",") if p.strip()]
    # de-dup while keeping order
    seen = set()
    out = []
    for t in parts:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

@st.cache_data(ttl=60*30, show_spinner=False)
def fetch_ohlc(ticker: str, start_dt: date, end_dt: date) -> pd.DataFrame:
    """
    Fetch daily OHLC for [start_dt - 10d, end_dt + 1d] to allow finding nearest previous trading day.
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

    # yfinance sometimes returns multi-index columns if multiple tickers; we fetch one at a time so it should be flat
    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    # Keep only needed columns
    cols = [c for c in ["High", "Low", "Open", "Close", "Volume"] if c in df.columns]
    return df[cols]

def nearest_prev_trading_row(df: pd.DataFrame, target_dt: date) -> pd.Series | None:
    """
    Return row for target_dt if exists; else nearest previous available trading day row.
    """
    if df is None or df.empty:
        return None
    t = pd.to_datetime(target_dt)
    # all dates <= target
    eligible = df[df.index <= t]
    if eligible.empty:
        return None
    return eligible.iloc[-1]

def mid_from_row(row: pd.Series) -> float | None:
    if row is None:
        return None
    if "High" not in row or "Low" not in row:
        return None
    hi = float(row["High"])
    lo = float(row["Low"])
    return (hi + lo) / 2.0

def fmt_money(x: float) -> str:
    # Accounting-style-ish (negative in parentheses)
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
with st.sidebar:
    st.header("INPUTS")
    raw_tickers = st.text_input("TICKERS (comma-separated)", value="CLOZ,SPY")
    amt = st.number_input("AMOUNT ($)", min_value=0.0, value=80000.0, step=1000.0)
    sd = st.date_input("START DATE", value=date(2025, 2, 24))
    ed = st.date_input("END DATE", value=date(2025, 4, 7))

    st.markdown("---")
    st.caption("Mid Price = (High + Low) / 2")
    run = st.button("RUN COMPARISON")

# ----------------------------
# Main
# ----------------------------
tickers = parse_tickers(raw_tickers)

if run:
    if not tickers:
        st.error("Enter at least one ticker (comma-separated).")
        st.stop()

    if ed < sd:
        st.error("End Date must be on/after Start Date.")
        st.stop()

    rows = []
    errors = []

    with st.spinner("Pulling daily High/Low data..."):
        for tkr in tickers:
            df = fetch_ohlc(tkr, sd, ed)
            if df.empty:
                errors.append(f"{tkr}: no data returned (check ticker).")
                continue

            r_s = nearest_prev_trading_row(df, sd)
            r_e = nearest_prev_trading_row(df, ed)

            if r_s is None:
                errors.append(f"{tkr}: no trading day found on/before start date.")
                continue
            if r_e is None:
                errors.append(f"{tkr}: no trading day found on/before end date.")
                continue

            s_used = pd.to_datetime(r_s.name).date()
            e_used = pd.to_datetime(r_e.name).date()

            s_hi, s_lo = float(r_s["High"]), float(r_s["Low"])
            e_hi, e_lo = float(r_e["High"]), float(r_e["Low"])

            s_mid = (s_hi + s_lo) / 2.0
            e_mid = (e_hi + e_lo) / 2.0

            chg = (e_mid / s_mid) - 1.0 if s_mid != 0 else None
            pnl = amt * chg if chg is not None else None

            rows.append({
                "TKR": tkr,
                "SD": s_used.isoformat(),
                "ED": e_used.isoformat(),
                "S_HI": s_hi,
                "S_LO": s_lo,
                "S_MID": s_mid,
                "E_HI": e_hi,
                "E_LO": e_lo,
                "E_MID": e_mid,
                "CHG%": chg,
                "PNL$": pnl,
            })

    if errors:
        st.warning("SOME TICKERS HAD ISSUES:\n\n- " + "\n- ".join(errors))

    if not rows:
        st.error("No results to display.")
        st.stop()

    out = pd.DataFrame(rows)

    # Sort by worst loss (most negative PNL$) first
    out = out.sort_values(by="PNL$", ascending=True).reset_index(drop=True)

    # Display summary metrics
    worst = out.iloc[0]
    best = out.iloc[-1]

    c1, c2, c3 = st.columns(3)
    c1.metric("WORST TKR", worst["TKR"])
    c2.metric("WORST P/L", fmt_money(float(worst["PNL$"])))
    c3.metric("WORST %", fmt_pct(float(worst["CHG%"])))

    st.markdown("---")

    # Format table for display
    show = out.copy()
    show["S_HI"] = show["S_HI"].map(lambda x: f"{x:,.2f}")
    show["S_LO"] = show["S_LO"].map(lambda x: f"{x:,.2f}")
    show["S_MID"] = show["S_MID"].map(lambda x: f"{x:,.2f}")
    show["E_HI"] = show["E_HI"].map(lambda x: f"{x:,.2f}")
    show["E_LO"] = show["E_LO"].map(lambda x: f"{x:,.2f}")
    show["E_MID"] = show["E_MID"].map(lambda x: f"{x:,.2f}")
    show["CHG%"] = show["CHG%"].map(lambda x: fmt_pct(float(x)))
    show["PNL$"] = show["PNL$"].map(lambda x: fmt_money(float(x)))

    st.subheader("RESULTS (RANKED BY WORST LOSS)")
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Simple callout: compare worst vs best
    st.subheader("QUICK READ")
    st.write(
        f"- Worst loss: **{worst['TKR']}** at **{fmt_money(float(worst['PNL$']))}** "
        f"from {worst['SD']} → {worst['ED']} (mid-price)."
    )
    st.write(
        f"- Best (least loss / most gain): **{best['TKR']}** at **{fmt_money(float(best['PNL$']))}** "
        f"from {best['SD']} → {best['ED']} (mid-price)."
    )

else:
    st.info("Enter inputs in the left sidebar, then click **RUN COMPARISON**.")

