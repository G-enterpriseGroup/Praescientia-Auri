import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividend Income Calculator", layout="centered")

# ---------- Helpers (cached where useful) ----------

@st.cache_data(show_spinner=False, ttl=15 * 60)
def _get_ticker(ticker: str):
    return yf.Ticker(ticker)

@st.cache_data(show_spinner=False, ttl=5 * 60)
def get_stock_price(ticker: str):
    """
    Fetch the latest price using multiple fallbacks.
    """
    try:
        t = _get_ticker(ticker)
        # Try fast_info first (quick); fallback to 1d history
        price = getattr(t, "fast_info", {}).get("last_price")
        if price is None:
            hist = t.history(period="1d", auto_adjust=False)
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return float(price) if price is not None else None
    except Exception:
        return None

@st.cache_data(show_spinner=False, ttl=6 * 60 * 60)
def get_full_security_name(ticker: str):
    """
    Fetch the long security name; fallback to ticker if unavailable.
    """
    try:
        t = _get_ticker(ticker)
        # yfinance .info can be slow/spotty; try fast_info “shortName” first if available
        name = getattr(t, "fast_info", {}).get("shortName")
        if not name:
            info = getattr(t, "info", {}) or {}
            name = info.get("longName") or info.get("shortName")
        return name if name else ticker
    except Exception:
        return ticker

@st.cache_data(show_spinner=False, ttl=6 * 60 * 60)
def get_ttm_dividend_per_share(ticker: str):
    """
    Total dividends per share paid in the last 365 days (TTM) via Yahoo Finance.
    Returns float amount per share over last 12 months.
    """
    try:
        t = _get_ticker(ticker)
        end = datetime.utcnow()
        start = end - timedelta(days=370)  # small buffer
        div = t.dividends
        if div is None or div.empty:
            return 0.0
        # Filter to last ~12 months and sum
        div_ttm = div[div.index >= start].sum()
        return float(div_ttm) if div_ttm is not None else 0.0
    except Exception:
        return 0.0

@st.cache_data(show_spinner=False, ttl=6 * 60 * 60)
def is_etf_ticker(ticker: str):
    """
    Heuristic via quoteType.
    """
    try:
        info = _get_ticker(ticker).info or {}
        qt = str(info.get("quoteType", "")).lower()
        return "etf" in qt
    except Exception:
        return False


def calculate_projected_income(ticker: str, days: int, quantity: float):
    """
    Uses TTM dividends from Yahoo (per-share) for yield and projection.
    """
    price = get_stock_price(ticker)
    if price is None or price <= 0:
        return {"error": f"Could not fetch a valid price for '{ticker}'."}

    ttm_div_ps = get_ttm_dividend_per_share(ticker)  # per share, last 12 months
    name = get_full_security_name(ticker)

    total_cost = price * quantity
    annual_div_yield_pct = (ttm_div_ps / price) * 100 if price else 0.0

    # Projected income assuming the TTM run-rate is representative
    daily_div_ps = ttm_div_ps / 365.0
    projected_income = daily_div_ps * quantity * days

    return {
        "security_name": name,
        "is_etf": is_etf_ticker(ticker),
        "projected_income": projected_income,
        "stock_price": price,
        "total_cost": total_cost,
        "dividend_yield": annual_div_yield_pct,
        "ttm_div_ps": ttm_div_ps,
    }

# ---------- UI ----------

st.title("Dividend Income Calculator")

with st.form("inputs"):
    ticker = st.text_input("Ticker Symbol").strip().upper()
    # No minimums; you can enter any positive integer/float (days & quantity validated below)
    days = st.number_input("Number of Days to Hold", value=365, step=1, format="%d")
    quantity = st.number_input("Quantity of Shares Held", value=100.0, step=1.0)
    submitted = st.form_submit_button("Calculate")

if submitted:
    # Basic validation without arbitrary caps
    if not ticker:
        st.warning("Please enter a valid ticker symbol.")
    elif days <= 0:
        st.warning("Days must be greater than 0.")
    elif quantity <= 0:
        st.warning("Quantity must be greater than 0.")
    else:
        results = calculate_projected_income(ticker, int(days), float(quantity))
        if "error" in results:
            st.error(results["error"])
        else:
            st.subheader(f"Financial Summary for {ticker}")
            st.write(f"**Security Name:** {results['security_name']}")
            st.write(f"**Current Stock Price:** ${results['stock_price']:,.2f}")
            st.write(f"**Total Investment Cost:** ${results['total_cost']:,.2f}")
            st.write(f"**TTM Dividend (per share):** ${results['ttm_div_ps']:,.4f}")
            st.write(f"**Dividend Yield (TTM):** {results['dividend_yield']:.2f}%")
            st.write(f"**Projected Dividend Income over {int(days)} days:** ${results['projected_income']:,.2f}")

            with st.expander("Details / Assumptions"):
                st.markdown(
                    "- Dividend data uses **TTM** from Yahoo Finance (sum of dividends paid over the last 12 months).\n"
                    "- Projected income assumes the TTM dividend rate continues pro-rata by day.\n"
                    "- Prices and dividends can change; refresh to update cached data."
                )
