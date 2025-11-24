import streamlit as st
import yfinance as yf
import pandas as pd

# =========================
# PAGE SETUP + THEME (BLOOMBERG STYLE)
# =========================
st.set_page_config(page_title="Tightest Breakeven Finder", layout="wide", page_icon="📊")

BLOOM_ORANGE = "#ff9f1c"

st.markdown(
    f"""
    <style>
    html, body, [class*="stApp"] {{
        background-color: #050608;
        color: #f4f4f4;
        font-family: "Menlo", "Consolas", "Roboto Mono", monospace;
    }}
    .main {{
        background-color: #050608;
    }}
    .metric-label {{
        font-size: 0.75rem;
        color: #9fa4ad;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    .metric-value-main {{
        font-size: 1.3rem;
        font-weight: 700;
        color: {BLOOM_ORANGE};
    }}
    .metric-value-sub {{
        font-size: 0.95rem;
        font-weight: 600;
        color: #f4f4f4;
    }}
    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }}
    thead tr th {{
        background-color: #11141a !important;
        color: {BLOOM_ORANGE} !important;
        border-bottom: 1px solid #333 !important;
    }}
    tbody tr td {{
        color: #f4f4f4 !important;
        border-color: #222 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Tightest ATM Breakeven (Call & Put)")
st.caption("For a ticker + expiration: show the single call and put with the tightest breakeven vs spot.")


# =========================
# HELPERS
# =========================
def get_spot(ticker: str) -> float:
    tk = yf.Ticker(ticker)
    hist = tk.history(period="1d")
    if hist.empty:
        raise ValueError(f"No price history for {ticker}")
    return float(hist["Close"].iloc[-1])


def get_chain(ticker: str, expiration: str):
    tk = yf.Ticker(ticker)
    chain = tk.option_chain(expiration)
    return chain.calls.copy(), chain.puts.copy()


def find_best_option(df: pd.DataFrame, side: str, spot: float, atm_window: float):
    """
    From one side (calls OR puts), find the single contract with
    breakeven closest to spot within ±atm_window of spot.
    Returns dict or None.
    """
    if df.empty:
        return None

    # Mid price
    df["mid"] = (df["bid"].fillna(0) + df["ask"].fillna(0)) / 2
    df.loc[df["mid"] <= 0, "mid"] = df["lastPrice"]

    # Filter ATM
    df = df[df["strike"] > 0]
    df = df[(df["strike"] - spot).abs() / spot <= atm_window]
    if df.empty:
        return None

    # Breakeven + distance
    if side == "CALL":
        df["breakeven"] = df["strike"] + df["mid"]
    else:  # PUT
        df["breakeven"] = df["strike"] - df["mid"]

    df["distance"] = (df["breakeven"] - spot).abs()

    # Pick row with smallest distance
    best = df.loc[df["distance"].idxmin()]

    return {
        "side": side,
        "strike": float(best["strike"]),
        "mid": float(best["mid"]),
        "breakeven": float(best["breakeven"]),
        "distance": float(best["distance"]),
        "volume": float(best.get("volume", 0)),
        "oi": float(best.get("openInterest", 0)),
        "iv": float(best.get("impliedVolatility", 0)),
    }


def find_best_call_put_for_exp(
    ticker: str,
    expiration: str,
    atm_window: float = 0.05,
):
    """
    For ticker + expiration:
    - Get spot
    - Get calls & puts
    - Return best call + best put (tightest breakeven vs spot)
    """
    spot = get_spot(ticker)
    calls_df, puts_df = get_chain(ticker, expiration)

    today = pd.Timestamp.today().normalize()
    exp_date = pd.to_datetime(expiration)
    dte = (exp_date - today).days

    best_call = find_best_option(calls_df, "CALL", spot, atm_window)
    best_put = find_best_option(puts_df, "PUT", spot, atm_window)

    return spot, dte, best_call, best_put


# =========================
# SIDEBAR
# =========================
st.sidebar.header("Settings")

ticker = st.sidebar.text_input("Ticker", value="SPY").upper().strip()

atm_pct = st.sidebar.slider(
    "ATM window (±% from spot)",
    min_value=1.0,
    max_value=15.0,
    value=5.0,
    step=1.0,
)
atm_window = atm_pct / 100.0  # convert to decimal


# =========================
# MAIN
# =========================
if not ticker:
    st.info("Enter a ticker on the left to begin.")
else:
    try:
        tk = yf.Ticker(ticker)
        expirations = tk.options

        if not expirations:
            st.error(f"No options listed for {ticker}.")
        else:
            exp = st.sidebar.selectbox(
                "Expiration",
                options=expirations,
                index=0,
                key="exp_select",
            )

            # Core calc: best call + best put for this expiration
            spot, dte, best_call, best_put = find_best_call_put_for_exp(
                ticker=ticker,
                expiration=exp,
                atm_window=atm_window,
            )

            # Header metrics
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown('<div class="metric-label">TICKER</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value-main">{ticker}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="metric-label">SPOT</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value-main">${spot:,.2f}</div>', unsafe_allow_html=True)
            with c3:
                st.markdown('<div class="metric-label">EXP / DTE</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="metric-value-main">{exp} · {dte}d</div>',
                    unsafe_allow_html=True
                )

            st.subheader("Tightest Breakeven (Call & Put)")

            if not best_call and not best_put:
                st.warning("No ATM options found with current filters. Try widening the ATM window.")
            else:
                col_call, col_put = st.columns(2)

                # ---- CALL BOX ----
                with col_call:
                    st.markdown('<div class="metric-label">BEST CALL (tightest BE)</div>', unsafe_allow_html=True)
                    if best_call:
                        st.markdown(
                            f'<div class="metric-value-main">Strike {best_call["strike"]:,.2f}</div>',
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f'<div class="metric-value-sub">Cost (mid): ${best_call["mid"]:,.2f}</div>',
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f'<div class="metric-value-sub">Breakeven: ${best_call["breakeven"]:,.2f}</div>',
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f'<div class="metric-value-sub">Distance to spot: ${best_call["distance"]:,.2f}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown('<div class="metric-value-sub">No call found in ATM range.</div>', unsafe_allow_html=True)

                # ---- PUT BOX ----
                with col_put:
                    st.markdown('<div class="metric-label">BEST PUT (tightest BE)</div>', unsafe_allow_html=True)
                    if best_put:
                        st.markdown(
                            f'<div class="metric-value-main">Strike {best_put["strike"]:,.2f}</div>',
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f'<div class="metric-value-sub">Cost (mid): ${best_put["mid"]:,.2f}</div>',
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f'<div class="metric-value-sub">Breakeven: ${best_put["breakeven"]:,.2f}</div>',
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f'<div class="metric-value-sub">Distance to spot: ${best_put["distance"]:,.2f}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown('<div class="metric-value-sub">No put found in ATM range.</div>', unsafe_allow_html=True)

                # Small summary table for both (nice to see side-by-side data)
                summary_rows = []
                if best_call:
                    summary_rows.append({
                        "SIDE": "CALL",
                        "STK": best_call["strike"],
                        "MID": best_call["mid"],
                        "BE": best_call["breakeven"],
                        "DIST": best_call["distance"],
                        "VOL": best_call["volume"],
                        "OI": best_call["oi"],
                        "IV": best_call["iv"],
                    })
                if best_put:
                    summary_rows.append({
                        "SIDE": "PUT",
                        "STK": best_put["strike"],
                        "MID": best_put["mid"],
                        "BE": best_put["breakeven"],
                        "DIST": best_put["distance"],
                        "VOL": best_put["volume"],
                        "OI": best_put["oi"],
                        "IV": best_put["iv"],
                    })

                if summary_rows:
                    st.markdown("---")
                    st.markdown("**Summary (Best Call & Put for this Expiration)**")
                    df_summary = pd.DataFrame(summary_rows)
                    styled = (
                        df_summary.style
                        .format({
                            "STK": "{:,.2f}",
                            "MID": "{:,.2f}",
                            "BE": "{:,.2f}",
                            "DIST": "{:,.2f}",
                            "VOL": "{:,.0f}",
                            "OI": "{:,.0f}",
                            "IV": "{:.2%}",
                        })
                    )
                    st.dataframe(styled, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
