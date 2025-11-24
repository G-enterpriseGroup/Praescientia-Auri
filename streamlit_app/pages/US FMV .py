# spy_spym_fair_value_spy_base_app.py

"""
Streamlit Fair Value Dashboard for SPY & SPYM (SPY as Base)
Bloomberg-style dark theme with orange accents.

Run:
    streamlit run spy_spym_fair_value_spy_base_app.py
"""

import yfinance as yf
import streamlit as st
import pandas as pd
from statistics import mean
import json
import streamlit.components.v1 as components

# -------------------------------
# CONSTANTS
# -------------------------------
SPX_TICKER = "^GSPC"
SPY_TICKER = "SPY"
SPYM_TICKER = "SPYM"
BANK_NAMES = ["JPM", "GS", "BofA", "MS", "Citi"]

# Major global benchmarks to show on the globe (expanded list)
GLOBAL_MARKETS = [
    # Americas
    {"name": "US · SPX",        "ticker": "^GSPC",    "lat": 40.7128,  "lng": -74.0060},   # New York
    {"name": "CA · S&P/TSX",    "ticker": "^GSPTSE",  "lat": 43.6532,  "lng": -79.3832},   # Toronto
    {"name": "MX · IPC",        "ticker": "^MXX",     "lat": 19.4326,  "lng": -99.1332},   # Mexico City
    {"name": "BR · Bovespa",    "ticker": "^BVSP",    "lat": -23.5505, "lng": -46.6333},   # São Paulo

    # Europe
    {"name": "UK · FTSE 100",   "ticker": "^FTSE",    "lat": 51.5074,  "lng": -0.1278},    # London
    {"name": "EU · STOXX 50",   "ticker": "^STOXX50E","lat": 48.8566,  "lng": 2.3522},     # Paris
    {"name": "DE · DAX",        "ticker": "^GDAXI",   "lat": 50.1109,  "lng": 8.6821},     # Frankfurt
    {"name": "FR · CAC 40",     "ticker": "^FCHI",    "lat": 48.8566,  "lng": 2.3522},     # Paris
    {"name": "CH · SMI",        "ticker": "^SSMI",    "lat": 47.3769,  "lng": 8.5417},     # Zurich
    {"name": "ES · IBEX 35",    "ticker": "^IBEX",    "lat": 40.4168,  "lng": -3.7038},    # Madrid
    {"name": "IT · FTSE MIB",   "ticker": "FTSEMIB.MI","lat": 45.4642, "lng": 9.1900},     # Milan

    # Asia-Pacific
    {"name": "JP · Nikkei 225", "ticker": "^N225",    "lat": 35.6895,  "lng": 139.6917},   # Tokyo
    {"name": "HK · Hang Seng",  "ticker": "^HSI",     "lat": 22.3193,  "lng": 114.1694},   # Hong Kong
    {"name": "CN · SSE Comp",   "ticker": "000001.SS","lat": 31.2304,  "lng": 121.4737},   # Shanghai
    {"name": "TW · TAIEX",      "ticker": "^TWII",    "lat": 25.0330,  "lng": 121.5654},   # Taipei
    {"name": "KR · KOSPI",      "ticker": "^KS11",    "lat": 37.5665,  "lng": 126.9780},   # Seoul
    {"name": "IN · Sensex",     "ticker": "^BSESN",   "lat": 19.0760,  "lng": 72.8777},    # Mumbai
    {"name": "SG · STI",        "ticker": "^STI",     "lat": 1.3521,   "lng": 103.8198},   # Singapore
    {"name": "AU · ASX 200",    "ticker": "^AXJO",    "lat": -33.8688, "lng": 151.2093},   # Sydney
    {"name": "NZ · NZX 50",     "ticker": "^NZ50",    "lat": -41.2865, "lng": 174.7762},   # Wellington

    # Middle East & Africa
    {"name": "ZA · Top 40",     "ticker": "^JTOPI",   "lat": -26.2041, "lng": 28.0473},    # Johannesburg
    {"name": "SA · TASI",       "ticker": "^TASI",    "lat": 24.7136,  "lng": 46.6753},    # Riyadh
]


# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="Fair Value Dashboard | SPY & SPYM",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------
# BLOOMBERG-LIKE THEME (CSS)
# -------------------------------
st.markdown(
    """
    <style>
    /* Global background + font */
    html, body, [class*="stApp"] {
        background-color: #050608;
        color: #f4f4f4;
        font-family: "Menlo", "Consolas", "Roboto Mono", monospace;
    }

    /* Main container */
    .main {
        background-color: #050608;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #101317;
        border-right: 1px solid #ff9f1c33;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffb347;
    }

    /* Headers */
    h1, h2, h3 {
        color: #ffb347;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Top metrics cards */
    .metric-title {
        font-size: 0.8rem;
        color: #ff9f1c;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #fefefe;
    }

    /* Dataframe tweaks */
    .blank[data-testid="stTable"] {
        background-color: #050608;
    }
    table {
        border-collapse: collapse !important;
    }
    thead tr {
        background-color: #15191f !important;
        border-bottom: 1px solid #ff9f1c66 !important;
    }
    thead th {
        color: #ffb347 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.8rem !important;
    }
    tbody tr {
        background-color: #050608 !important;
    }
    tbody tr:nth-child(even) {
        background-color: #090c12 !important;
    }
    td {
        color: #f4f4f4 !important;
        font-size: 0.85rem !important;
    }

    /* Slider, radio, etc. accent colors */
    div[data-baseweb="slider"] > div {
        color: #ffb347;
    }
    div[role="radiogroup"] > label > div:first-child {
        border-color: #ff9f1c !important;
    }
    div[role="radiogroup"] label span {
        color: #f4f4f4 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------
# HELPERS
# -------------------------------
@st.cache_data(ttl=60)
def get_last_price(ticker: str) -> float:
    """Fetch latest close from Yahoo Finance (cached briefly)."""
    data = yf.Ticker(ticker).history(period="1d")
    if data.empty:
        raise ValueError(f"No price data for {ticker}")
    return float(data["Close"].iloc[-1])


def calc_fair_value_from_market(price: float, is_undervalued: bool, pct: float) -> float:
    """
    pct is ALWAYS positive (example: 5.6 for 5.6%).

    UNDERVALUE X%:
        price = FV * (1 - X/100)
        FV    = price / (1 - X/100)

    OVERVALUED X%:
        price = FV * (1 + X/100)
        FV    = price / (1 + X/100)
    """
    if pct <= 0:
        raise ValueError("Percent must be positive (e.g. 5.6).")

    factor = 1.0 - pct / 100.0 if is_undervalued else 1.0 + pct / 100.0
    if factor == 0:
        raise ValueError("Factor became zero; check your inputs.")
    return price / factor


def street_fair_values_for_etf(etf_price: float, spx_price: float, bank_targets: dict) -> dict:
    """
    Map each bank's SPX target into ETF fair value using ETF/SPX ratio.
    """
    if spx_price <= 0:
        raise ValueError("SPX price must be positive.")

    k = etf_price / spx_price
    return {bank: k * float(target) for bank, target in bank_targets.items()}


def color_upsides(val):
    """Bloomberg-style: green for positive, red for negative, dim grey for near flat."""
    if pd.isna(val):
        return ""
    try:
        v = float(val)
    except ValueError:
        return ""
    if v > 0.5:
        return "color: #08ff7e; font-weight: 600;"   # bright green
    elif v < -0.5:
        return "color: #ff4d4d; font-weight: 600;"   # red
    else:
        return "color: #aaaaaa;"                     # muted grey


@st.cache_data(ttl=600)
def get_global_index_changes(markets):
    """
    For each index:
      - Last close
      - 1D % change (vs previous close)
      - 5D % change (vs ~5 trading days ago)
      - % from 52-week high (approx using last 1y)
    Using Yahoo Finance daily history.
    """
    results = []
    for m in markets:
        last = 0.0
        chg_1d = 0.0
        chg_5d = 0.0
        off_high_pct = 0.0
        try:
            hist = yf.Ticker(m["ticker"]).history(period="1y")
            close = hist["Close"].dropna()
            if not close.empty:
                last = float(close.iloc[-1])

                if close.size >= 2:
                    prev1 = float(close.iloc[-2])
                    if prev1 > 0:
                        chg_1d = (last - prev1) / prev1 * 100.0

                if close.size >= 6:
                    prev5 = float(close.iloc[-6])
                    if prev5 > 0:
                        chg_5d = (last - prev5) / prev5 * 100.0

                high_52w = float(close.max())
                if high_52w > 0:
                    off_high_pct = (last - high_52w) / high_52w * 100.0
        except Exception:
            pass

        results.append(
            {
                "name": m["name"],
                "lat": m["lat"],
                "lng": m["lng"],
                "last": float(last),
                "chg_1d": float(chg_1d),
                "chg_5d": float(chg_5d),
                "off_high_pct": float(off_high_pct),
            }
        )
    return results


# -------------------------------
# SIDEBAR: CONTROLS
# -------------------------------
st.sidebar.title("Market Inputs")

market_state = st.sidebar.radio(
    "Overall market condition",
    options=["Undervalued", "Overvalued"],
    index=0,
)
is_undervalued = (market_state == "Undervalued")

market_pct = st.sidebar.number_input(
    "Magnitude (%)",
    min_value=0.01,
    max_value=100.0,
    value=5.6,
    step=0.1,
    help="Enter as a positive number, e.g. 5.6 for 5.6%. "
         "Use Morningstar's 'Undervalued X%' as X if you want.",
)

st.sidebar.markdown("---")

use_banks = st.sidebar.checkbox(
    "Add bank SPX targets as benchmarks",
    value=False,
    help="If checked, you can enter SPX targets for JPM, GS, BofA, MS, Citi.",
)

bank_targets = {}
if use_banks:
    st.sidebar.subheader
