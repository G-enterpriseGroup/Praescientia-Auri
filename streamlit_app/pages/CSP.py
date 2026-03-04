import math
from datetime import datetime, date
import streamlit as st
import yfinance as yf
import pandas as pd

# =========================
# Helpers (no extra deps)
# =========================
def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _parse_exp_date(exp_str: str) -> date:
    return datetime.strptime(exp_str, "%Y-%m-%d").date()

def _safe_float(x, default=None):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def _get_spot_price(ticker: yf.Ticker) -> float | None:
    # Robust spot fetch across yfinance versions
    try:
        fi = getattr(ticker, "fast_info", None)
        if fi:
            for k in ("last_price", "lastPrice", "regularMarketPrice"):
                v = fi.get(k) if isinstance(fi, dict) else getattr(fi, k, None)
                if v:
                    return float(v)
    except Exception:
        pass

    try:
        info = ticker.info or {}
        for k in ("regularMarketPrice", "currentPrice", "previousClose"):
            v = info.get(k)
            if v:
                return float(v)
    except Exception:
        pass

    try:
        h = ticker.history(period="5d", interval="1d")
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except Exception:
        pass

    return None

def _risk_neutral_prob_itm_put(S, K, T, r, q, iv):
    """
    Risk-neutral probability put expires ITM: P(S_T < K) = N(-d2)
    Black-Scholes. Returns None if inputs not usable.
    """
    if not S or not K or not T or T <= 0:
        return None
    if iv is None or iv <= 0:
        return None

    try:
        sqrtT = math.sqrt(T)
        d1 = (math.log(S / K) + (r - q + 0.5 * iv * iv) * T) / (iv * sqrtT)
        d2 = d1 - iv * sqrtT
        return _norm_cdf(-d2)
    except Exception:
        return None

# =========================
# Core: fetch + CSP analysis
# =========================
@st.cache_data(show_spinner=False, ttl=60)
def fetch_puts_with_analysis(
    ticker_symbol: str,
    r_pct: float,
    q_pct: float,
    price_source: str,
) -> tuple[pd.DataFrame, float | None]:
    t = yf.Ticker(ticker_symbol)
    expirations = t.options or []
    spot = _get_spot_price(t)

    all_rows = []
    today = datetime.now().date()

    r = r_pct / 100.0
    q = q_pct / 100.0

    for exp_str in expirations:
        exp_date = _parse_exp_date(exp_str)
        dte = (exp_date - today).days
        if dte <= 0:
            continue

        try:
            chain = t.option_chain(exp_str)
            puts = chain.puts.copy()
            if puts.empty:
                continue

            keep = [
                "contractSymbol", "strike", "bid", "ask", "lastPrice",
                "impliedVolatility", "volume", "openInterest", "inTheMoney"
            ]
            cols = [c for c in keep if c in puts.columns]
            puts = puts[cols].copy()

            rename = {
                "contractSymbol": "Contract",
                "strike": "Strike",
                "bid": "Bid Price",
                "ask": "Ask Price",
                "lastPrice": "Last Price",
                "impliedVolatility": "IV",
                "volume": "Volume",
                "openInterest": "OI",
                "inTheMoney": "ITM?",
            }
            puts.rename(columns=rename, inplace=True)

            puts["Expiration"] = exp_str
            puts["DTE"] = dte
            puts["Spot"] = spot

            puts["% OTM"] = puts.apply(
                lambda r_: (
                    (float(r_["Spot"]) - float(r_["Strike"])) / float(r_["Spot"])
                    if r_.get("Spot") and r_.get("Strike") and float(r_["Spot"]) != 0 else None
                ),
                axis=1
            )

            puts["Premium (Ask)"] = puts["Ask Price"]
            puts["Premium (Bid)"] = puts["Bid Price"]

            puts["BE (Ask)"] = puts.apply(
                lambda r_: (
                    float(r_["Strike"]) - float(r_["Premium (Ask)"])
                    if _safe_float(r_.get("Strike")) is not None and _safe_float(r_.get("Premium (Ask)")) is not None
                    else None
                ),
                axis=1
            )
            puts["BE (Bid)"] = puts.apply(
                lambda r_: (
                    float(r_["Strike"]) - float(r_["Premium (Bid)"])
                    if _safe_float(r_.get("Strike")) is not None and _safe_float(r_.get("Premium (Bid)")) is not None
                    else None
                ),
                axis=1
            )

            puts["Cash Req ($)"] = puts.apply(
                lambda r_: (float(r_["Strike"]) * 100.0 if _safe_float(r_.get("Strike")) is not None else None),
                axis=1
            )

            puts["Yield % (Ask)"] = puts.apply(
                lambda r_: (
                    (float(r_["Premium (Ask)"]) / float(r_["Strike"])) * 100.0
                    if _safe_float(r_.get("Strike")) not in (None, 0.0) and _safe_float(r_.get("Premium (Ask)")) is not None
                    else None
                ),
                axis=1
            )
            puts["Yield % (Bid)"] = puts.apply(
                lambda r_: (
                    (float(r_["Premium (Bid)"]) / float(r_["Strike"])) * 100.0
                    if _safe_float(r_.get("Strike")) not in (None, 0.0) and _safe_float(r_.get("Premium (Bid)")) is not None
                    else None
                ),
                axis=1
            )

            puts["Ann. Yield % (Ask)"] = puts.apply(
                lambda r_: (
                    ((float(r_["Premium (Ask)"]) / float(r_["Strike"])) / (float(r_["DTE"]) / 365.0)) * 100.0
                    if _safe_float(r_.get("Strike")) not in (None, 0.0)
                    and _safe_float(r_.get("Premium (Ask)")) is not None
                    and _safe_float(r_.get("DTE")) not in (None, 0.0)
                    else None
                ),
                axis=1
            )
            puts["Ann. Yield % (Bid)"] = puts.apply(
                lambda r_: (
                    ((float(r_["Premium (Bid)"]) / float(r_["Strike"])) / (float(r_["DTE"]) / 365.0)) * 100.0
                    if _safe_float(r_.get("Strike")) not in (None, 0.0)
                    and _safe_float(r_.get("Premium (Bid)")) is not None
                    and _safe_float(r_.get("DTE")) not in (None, 0.0)
                    else None
                ),
                axis=1
            )

            def prob_assign_row(r_):
                S = _safe_float(r_.get("Spot"))
                K = _safe_float(r_.get("Strike"))
                iv = _safe_float(r_.get("IV"))
                T = _safe_float(r_.get("DTE"))
                if T is not None:
                    T = T / 365.0

                p_itm = _risk_neutral_prob_itm_put(S, K, T, r, q, iv)
                if p_itm is not None:
                    return p_itm

                if S and K and S > 0:
                    m = (S - K) / S
                    return max(0.01, min(0.99, 0.5 * math.exp(-10.0 * max(0.0, m))))
                return None

            puts["Prob Assign (Est)"] = puts.apply(prob_assign_row, axis=1)
            puts["Prob Expire W/O Assign (Est)"] = puts["Prob Assign (Est)"].apply(
                lambda x: (1.0 - x) if x is not None and not pd.isna(x) else None
            )

            def csp_score_row(r_):
                ay = _safe_float(r_.get("Ann. Yield % (Bid)"))
                potm = _safe_float(r_.get("% OTM"))
                p = _safe_float(r_.get("Prob Assign (Est)"))
                oi = _safe_float(r_.get("OI"), 0.0) or 0.0
                vol = _safe_float(r_.get("Volume"), 0.0) or 0.0

                if ay is None:
                    return None

                liq = math.log10(1.0 + oi) + 0.5 * math.log10(1.0 + vol)
                p_pen = (p * 100.0) if p is not None else 35.0
                otm_bonus = (potm * 100.0) if potm is not None else 0.0

                return ay + 0.25 * otm_bonus + 2.0 * liq - 0.6 * p_pen

            puts["CSP Score"] = puts.apply(csp_score_row, axis=1)
            all_rows.append(puts)

        except Exception:
            continue

    if not all_rows:
        return pd.DataFrame(), spot

    df = pd.concat(all_rows, ignore_index=True)

    for c in ["Strike", "Bid Price", "Ask Price", "Last Price", "IV", "Volume", "OI", "DTE", "Spot",
              "% OTM", "Yield % (Ask)", "Yield % (Bid)", "Ann. Yield % (Ask)", "Ann. Yield % (Bid)",
              "BE (Ask)", "BE (Bid)", "Cash Req ($)", "Prob Assign (Est)", "Prob Expire W/O Assign (Est)", "CSP Score"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df, spot


# =========================
# Streamlit UI
# =========================
def main():
    st.set_page_config(page_title="Cash-Secured Put Analyzer", layout="wide")
    st.title("Cash-Secured Put (CSP) Analyzer")

    colA, colB, colC, colD = st.columns([1.1, 1, 1, 1])
    with colA:
        ticker_symbol = st.text_input("Ticker", "AAPL").upper().strip()
    with colB:
        r_pct = st.number_input("Risk-Free Rate (%)", value=4.50, step=0.05)
    with colC:
        q_pct = st.number_input("Dividend Yield (%)", value=0.00, step=0.05)
    with colD:
        price_source = st.selectbox("Spot Price Source", ["Auto"], index=0)

    st.caption(
        "Notes: CSP seller typically receives **Bid** (not Ask). "
        "I show yields using both, but the default ranking uses **Bid** for realism."
    )

    # =========================
    # Filters + toggles
    # =========================
    st.subheader("Filters")

    t1, t2, t3, t4 = st.columns([1, 1, 1, 1])
    with t1:
        use_max_dte = st.toggle("Use Max DTE", value=True)
    with t2:
        use_min_oi = st.toggle("Use Min OI", value=True)
    with t3:
        use_max_prob = st.toggle("Use Max Prob Assign", value=True)
    with t4:
        use_min_otm = st.toggle("Use Min % OTM", value=True)

    f1, f2, f3, f4, f5 = st.columns([1, 1, 1, 1, 1])
    with f1:
        min_dte = st.number_input("Min DTE", value=7, step=1)
    with f2:
        max_dte = st.number_input("Max DTE", value=60, step=1, disabled=not use_max_dte)
    with f3:
        min_oi = st.number_input("Min OI", value=50, step=10, disabled=not use_min_oi)
    with f4:
        max_prob = st.slider("Max Prob Assign (Est)", 0.0, 1.0, 0.35, 0.01, disabled=not use_max_prob)
    with f5:
        min_otm = st.slider("Min % OTM", 0.0, 0.5, 0.05, 0.01, disabled=not use_min_otm)

    if st.button("Fetch CSP Ideas", type="primary"):
        with st.spinner("Pulling options chain + calculating CSP metrics..."):
            df, spot = fetch_puts_with_analysis(ticker_symbol, r_pct, q_pct, price_source)

        if df.empty:
            st.error(f"No put options data found for {ticker_symbol}.")
            return

        if spot is None or pd.isna(spot):
            st.warning("Could not reliably fetch spot price; probabilities/%OTM may be blank.")

        # Apply filters (respect toggles)
        view = df.copy()

        # Min DTE always on (you didn't ask for toggle)
        view = view[view["DTE"] >= min_dte]

        if use_max_dte:
            view = view[view["DTE"] <= max_dte]

        if use_min_oi and "OI" in view.columns:
            view = view[view["OI"].fillna(0) >= min_oi]

        if use_min_otm:
            view = view[view["% OTM"].fillna(0) >= min_otm]

        if use_max_prob:
            view = view[view["Prob Assign (Est)"].fillna(1.0) <= max_prob]

        view = view.sort_values(["CSP Score", "Ann. Yield % (Bid)"], ascending=[False, False])

        display_cols = [
            "Expiration", "DTE", "Contract",
            "Spot", "Strike", "% OTM",
            "Bid Price", "Ask Price",
            "Yield % (Bid)", "Ann. Yield % (Bid)",
            "BE (Bid)",
            "Prob Assign (Est)", "Prob Expire W/O Assign (Est)",
            "IV", "Volume", "OI",
            "Cash Req ($)",
            "CSP Score",
        ]
        display_cols = [c for c in display_cols if c in view.columns]

        fmt = view[display_cols].copy()

        def pct(x):
            return "" if pd.isna(x) else f"{x*100:,.1f}%"

        def pct100(x):
            return "" if pd.isna(x) else f"{x:,.2f}%"

        def money(x):
            return "" if pd.isna(x) else f"${x:,.2f}"

        def money0(x):
            return "" if pd.isna(x) else f"${x:,.0f}"

        if "Spot" in fmt.columns: fmt["Spot"] = fmt["Spot"].apply(money)
        if "Strike" in fmt.columns: fmt["Strike"] = fmt["Strike"].apply(money)
        if "Bid Price" in fmt.columns: fmt["Bid Price"] = fmt["Bid Price"].apply(money)
        if "Ask Price" in fmt.columns: fmt["Ask Price"] = fmt["Ask Price"].apply(money)
        if "BE (Bid)" in fmt.columns: fmt["BE (Bid)"] = fmt["BE (Bid)"].apply(money)
        if "Cash Req ($)" in fmt.columns: fmt["Cash Req ($)"] = fmt["Cash Req ($)"].apply(money0)

        if "% OTM" in fmt.columns:
            fmt["% OTM"] = fmt["% OTM"].apply(lambda x: "" if pd.isna(x) else f"{x*100:,.1f}%")

        for c in ["Yield % (Bid)", "Ann. Yield % (Bid)"]:
            if c in fmt.columns:
                fmt[c] = fmt[c].apply(pct100)

        for c in ["Prob Assign (Est)", "Prob Expire W/O Assign (Est)"]:
            if c in fmt.columns:
                fmt[c] = fmt[c].apply(pct)

        if "IV" in fmt.columns:
            fmt["IV"] = fmt["IV"].apply(lambda x: "" if pd.isna(x) else f"{x*100:,.1f}%")

        if "CSP Score" in fmt.columns:
            fmt["CSP Score"] = fmt["CSP Score"].apply(lambda x: "" if pd.isna(x) else f"{x:,.2f}")

        st.subheader("Top CSP candidates (filtered + ranked)")
        st.dataframe(fmt, use_container_width=True, hide_index=True)

        csv_bytes = view.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV (filtered + scored)",
            data=csv_bytes,
            file_name=f"{ticker_symbol}_csp_scored.csv",
            mime="text/csv",
        )

        with st.expander("Show grouped by expiration"):
            for exp, g in view.groupby("Expiration", sort=True):
                st.markdown(f"**Expiration: {exp}**  —  {len(g)} contracts")
                g2 = g.sort_values(["CSP Score"], ascending=False)
                st.dataframe(g2[display_cols].head(50), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
