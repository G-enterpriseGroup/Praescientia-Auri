import streamlit as st
import yfinance as yf
from datetime import datetime
import pandas as pd
import numpy as np

# ----------------- PAGE THEME -----------------
st.set_page_config(page_title="Dividend Income Calculator", layout="centered")

# Bloomberg Orange CSS
st.markdown("""
<style>
body { background-color: #0D0D0D; color: #FFA500; font-weight: bold; }
div.stButton > button { background-color: #FFA500; color: black; font-weight: bold; border-radius: 6px; }
div.stButton > button:hover { background-color: #FFB733; }
input, textarea, select {
    background-color: #1A1A1A !important;
    color: #FFA500 !important;
    border: 1px solid #FFA500 !important;
    font-weight: bold !important;
}
.css-1d391kg, .css-1n76uvr, .stTextInput {
    color: #FFA500 !important;
    font-weight: bold !important;
}
table { color: #FFA500 !important; }
th, td { color: #FFA500 !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

# ----------------- Data Helpers -----------------

@st.cache_data(ttl=15*60, show_spinner=False)
def get_price(ticker: str):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d", auto_adjust=False)
        if hist.empty:
            hist = t.history(period="5d", auto_adjust=False)
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None

@st.cache_data(ttl=6*60*60, show_spinner=False)
def get_name(ticker: str):
    try:
        t = yf.Ticker(ticker)
        finfo = getattr(t, "fast_info", None)
        if finfo and "longName" in finfo:
            return finfo["longName"]
        return ticker
    except:
        return ticker

@st.cache_data(ttl=6*60*60, show_spinner=False)
def get_dividends(ticker: str) -> pd.Series:
    try:
        s = yf.Ticker(ticker).dividends
        if s is None:
            return pd.Series(dtype=float)
        return s.astype(float)
    except:
        return pd.Series(dtype=float)

def infer_frequency(divs: pd.Series):
    if divs.empty or len(divs.index) < 3:
        return None, None
    dates = divs.index.sort_values()
    recent = dates[-6:] if len(dates) >= 6 else dates
    if len(recent) < 3:
        return None, None
    gaps = np.diff(recent.values).astype('timedelta64[D]').astype(int)
    if len(gaps) == 0:
        return None, None
    med = int(np.median(gaps))
    if 25 <= med <= 35:
        return "monthly", med
    if 70 <= med <= 100:
        return "quarterly", med
    if 150 <= med <= 210:
        return "semiannual", med
    if 330 <= med <= 390:
        return "annual", med
    return None, med

def estimate_amount_per_payment(divs: pd.Series, freq: str):
    if divs.empty:
        return 0.0
    tail = divs.tail(3).values
    if freq == "monthly":
        return float(np.mean(tail)) if len(tail) >= 3 else float(np.mean(divs.tail(2).values))
    if freq == "quarterly":
        return float(divs.iloc[-1])
    if len(divs) >= 2:
        return float(np.mean(divs.tail(2).values))
    return float(divs.iloc[-1])

def project_ex_dates(divs: pd.Series, days: int):
    today = pd.Timestamp(datetime.utcnow().date())
    if divs.empty:
        return []
    freq, avg_gap = infer_frequency(divs)
    last_ex = pd.Timestamp(divs.index.max().date())
    if avg_gap is None:
        return []
    horizon = today + pd.Timedelta(days=days)
    ex_dates = []
    next_date = last_ex + pd.Timedelta(days=avg_gap)
    while next_date < today:
        next_date += pd.Timedelta(days=avg_gap)
    while next_date < horizon:
        ex_dates.append(next_date)
        next_date += pd.Timedelta(days=avg_gap)
    return ex_dates, freq

def ttm_daily(divs: pd.Series):
    if divs.empty:
        return 0.0
    cutoff = pd.Timestamp(datetime.utcnow().date()) - pd.Timedelta(days=370)
    ttm = divs[divs.index >= cutoff].sum()
    return float(ttm) / 365.0

# ----------------- Calculation -----------------

def calculate_dividends_forward(ticker: str, days: int, qty: float):
    price = get_price(ticker)
    if price is None or price <= 0:
        return {"error": f"Could not fetch a valid price for '{ticker}'."}

    name = get_name(ticker)
    divs = get_dividends(ticker)

    schedule_out = []
    total_cash = 0.0
    used_model = "schedule"

    proj = project_ex_dates(divs, days)
    if isinstance(proj, tuple) and len(proj) == 2:
        ex_dates, freq = proj
        if ex_dates:
            amt_per = estimate_amount_per_payment(divs, freq)
            for d in ex_dates:
                cash = amt_per * qty
                schedule_out.append({
                    "ex_date": str(d.date()),
                    "per_share": amt_per,
                    "cash": cash
                })
                total_cash += cash
        else:
            used_model = "ttm_prorata"
    else:
        used_model = "ttm_prorata"

    if used_model == "ttm_prorata":
        daily_ps = ttm_daily(divs)
        total_cash = daily_ps * qty * max(days, 0)
        schedule_out = []

    total_cost = price * qty
    ttm_ps = float(divs.tail(370).sum()) if not divs.empty else 0.0
    yield_pct_ttm = (ttm_ps / price * 100.0) if price else 0.0

    return {
        "security_name": name,
        "price": price,
        "quantity": qty,
        "days": int(days),
        "total_investment": total_cost,
        "dividends_expected": total_cash,
        "method": used_model,
        "schedule": schedule_out,
        "ttm_div_per_share": ttm_ps,
        "ttm_yield_pct": yield_pct_ttm,
    }

# ----------------- UI -----------------

st.title("📈 Dividend Income Calculator (Bloomberg Orange Edition)")

with st.form("inputs"):
    ticker = st.text_input("Ticker Symbol").strip().upper()
    days = st.number_input("Number of Days (forward)", min_value=1, value=365, step=1)
    quantity = st.number_input("Quantity of Shares", min_value=1.0, value=100.0, step=1.0)
    submitted = st.form_submit_button("CALCULATE")

if submitted:
    if not ticker:
        st.warning("Please enter a valid ticker symbol.")
    else:
        res = calculate_dividends_forward(ticker, int(days), float(quantity))

        if "error" in res:
            st.error(res["error"])
        else:
            st.subheader(f"Summary for {ticker}")
            st.write(f"**Security Name:** {res['security_name']}")
            st.write(f"**Current Stock Price:** ${res['price']:,.2f}")
            st.write(f"**Total Investment:** ${res['total_investment']:,.2f}")
            st.write(f"**TTM Dividend (per share):** ${res['ttm_div_per_share']:,.4f}")
            st.write(f"**TTM Yield:** {res['ttm_yield_pct']:.2f}%")
            st.write(f"**Estimated Dividends (next {res['days']} days):** ${res['dividends_expected']:,.2f}")
            st.caption(f"Method: {res['method']}")

            if res["schedule"]:
                st.markdown("**Projected Ex-Dividend Dates**")
                df = pd.DataFrame(res["schedule"])
                df["cash"] = df["cash"].map(lambda x: f"${x:,.2f}")
                df["per_share"] = df["per_share"].map(lambda x: f"${x:,.4f}")
                st.dataframe(df, use_container_width=True)

            with st.expander("Notes"):
                st.markdown(
                    "- Ex-dates & amounts are inferred from history (issuer can change them).\n"
                    "- ETFs now fully supported.\n"
                    "- TTM fallback is used only if schedule cannot be inferred."
                )
