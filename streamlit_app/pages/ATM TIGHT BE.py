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

    /* Dataframe / table styling – VERY Bloomberg */
    [data-testid="stDataFrame"] {{
        border: 1px solid #333333;
        border-radius: 4px;
        background-color: #050608;
    }}

    [data-testid="stDataFrame"] thead tr th {{
        background-color: #11141a !important;
        color: {BLOOM_ORANGE} !important;
        border-bottom: 1px solid #333 !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    [data-testid="stDataFrame"] tbody tr td {{
        color: {BLOOM_ORANGE} !important;
        border-color: #222 !important;
        font-size: 0.82rem !important;
    }}

    [data-testid="stDataFrame"] tbody tr:nth-child(even) td {{
        background-color: #080a0f !important;
    }}

    [data-testid="stDataFrame"] tbody tr:nth-child(odd) td {{
        background-color: #050608 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Tightest ATM Breakeven (Call & Put)")
st.caption("For a ticker + expiration: show the single call and put with the tightest breakeven vs spot, plus total strangle cost.")


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
        df["br]()
