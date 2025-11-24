import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# =========================
# BASIC PAGE SETUP
# =========================
st.set_page_config(page_title="ATM Breakeven Finder", layout="wide", page_icon="📊")

st.markdown(
    """
    <style>
    html, body, [class*="stApp"] {
        background-color: #050608;
        color: #f4f4f4;
        font-family: "Menlo", "Consolas", "Roboto Mono", monospace;
    }
    .main {
        background-color: #050608;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #9fa4ad;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .metric-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f4f4f4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 ATM Breakeven Finder")
st.caption("Find the tightest call/put breakevens near the money for any ticker & expiration.")


# =========================
# CORE CALC FUNCTION
# =========================
def compute_tight_breakevens_for_exp(
    ticker: str,
    expiration: str,
    atm_window: float = 0.05,
    top_n: int = 20,
) -> pd.DataFrame:
    tk = yf.Ticker(ticker)

    # Spot
    hist = tk.history(period="1d")
    if hist.empty:
        raise ValueError(f"No price history for {ticker}")
    spot = float(hist["Close"].iloc[-1])

    # Option chain for that expiration
    chain = tk.option_chain(expiration)
    calls_df = chain.calls.copy()
    puts_df = chain.puts.copy()

    rows = []
    today = pd.Timestamp.today().normalize()
    exp_date = pd.to_datetime(expiration)
    dte = (exp_date - today).days

    def process_side(df: pd.DataFrame, side: str):
        nonlocal rows
        if df.empty:
            return

        # Mid price
        df["mid"] = (df["bid"].fillna(0) + df["ask"].fillna(0)) / 2
        df.loc[df["mid"] <= 0, "mid"] = df["lastPrice"]

        # ATM filter
        df = df[df["strike"] > 0]
        df = df[(df["strike"] - spot).abs() / spot <= atm_window]
        if df.empty:
            return

        # Breakeven
        if side == "CALL":
            df["breakeven"] = df["strike"] + df["mid"]
        else:
            df["breakeven"] = df["strike"] - df["mid"]

        df["distance"] = (df["breakeven"] - spot).abs()

        # Compact column names for you
        out = pd.DataFrame({
            "TCK": ticker,
            "SD": side,
            "EXP": expiration,
            "DTE": dte,
            "STK": df["strike"],
            "MID": df["mid"],
            "BE": df["breakeven"],
            "DIST": df["distance"],
            "VOL": df["volume"],
            "OI": df["openInterest"],
            "IV": df["impliedVolatility"],
            "SPOT": spot,
        })

        rows.extend(out.to_dict("records"))

    process_side(calls_df, "CALL")
    process_side(puts_df, "PUT")

    if not rows:
        raise ValueError("No ATM options found with current filters.")

    result = pd.DataFrame(rows)
    result = result.sort_values(["DIST", "DTE", "STK"]).reset_index(drop=True)
    return result.head(top_n)


# =========================
# SIDEBAR CONTROLS
# =========================
st.sidebar.header("Settings")

ticker = st.sidebar.text_input("Ticker", value="SPY").upper().strip()

atm_window = st.sidebar.slider(
    "ATM window (±% from spot)",
    min_value=1.0,
    max_value=15.0,
    value=5.0,
    step=1.0,
)
atm_window = atm_window / 100.0  # convert % to decimal

top_n = st.sidebar.slider(
    "Rows to show (top N by tightest DIST)",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
)

side_filter = st.sidebar.radio(
    "Side",
    options=["Both", "Calls only", "Puts only"],
    index=0,
)

load_btn = st.sidebar.button("🔄 Load options")


# =========================
# MAIN LOGIC
# =========================
if ticker and load_btn:
    try:
        tk = yf.Ticker(ticker)
        expirations = tk.options

        if not expirations:
            st.error(f"No options listed for {ticker}.")
        else:
            exp = st.selectbox("Select expiration date", options=expirations, index=0)

            if exp:
                df = compute_tight_breakevens_for_exp(
                    ticker=ticker,
                    expiration=exp,
                    atm_window=atm_window,
                    top_n=top_n,
                )

                # Apply side filter
                if side_filter == "Calls only":
                    df = df[df["SD"] == "CALL"]
                elif side_filter == "Puts only":
                    df = df[df["SD"] == "PUT"]

                if df.empty:
                    st.warning("No contracts match the current filters.")
                else:
                    spot_val = df["SPOT"].iloc[0]
                    dte_val = df["DTE"].iloc[0]

                    # Top metrics row
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown('<div class="metric-label">TICKER</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="metric-value">{ticker}</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown('<div class="metric-label">SPOT</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="metric-value">${spot_val:,.2f}</div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown('<div class="metric-label">EXP / DTE</div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="metric-value">{exp}  ·  {dte_val} days</div>',
                            unsafe_allow_html=True
                        )

                    st.subheader("Tightest Breakevens Near the Money")

                    # Format + style
                    display_df = df.copy()
                    display_df = display_df[[
                        "SD", "EXP", "DTE", "STK", "MID", "BE", "DIST", "VOL", "OI", "IV"
                    ]]

                    styled = (
                        display_df.style
                        .format({
                            "STK": "{:,.2f}",
                            "MID": "{:,.2f}",
                            "BE": "{:,.2f}",
                            "DIST": "{:,.2f}",
                            "IV": "{:.2%}",
                            "VOL": "{:,.0f}",
                            "OI": "{:,.0f}",
                        })
                        .background_gradient(subset=["DIST"], axis=0)
                    )

                    st.dataframe(styled, use_container_width=True)

                    st.caption(
                        "DIST = |breakeven − spot|. "
                        "Smaller DIST = tighter breakeven versus current price."
                    )

    except Exception as e:
        st.error(f"Error: {e}")

elif not load_btn:
    st.info("Enter a ticker on the left and click **Load options** to begin.")
