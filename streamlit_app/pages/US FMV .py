# spy_spym_fair_value_spy_base_app.py

"""
Streamlit Fair Value Dashboard for SPY & SPYM (SPY as Base)
Bloomberg-style dark theme with orange accents.

Features
--------
- Live prices from Yahoo Finance:
    - SPX (^GSPC)
    - SPY
    - SPYM

- You choose:
    - Market condition: UNDERVALUE / OVERVALUED
    - Magnitude in % (positive number, e.g. 5.6)

  TIP: When using Morningstar, type their
       US Market "Undervalued X%" number as X here.

Logic (for SPY):
    If UNDERVALUE X%:
        Price = FV * (1 - X/100)
        FV    = Price / (1 - X/100)

    If OVERVALUED X%:
        Price = FV * (1 + X/100)
        FV    = Price / (1 + X/100)

SPYM fair value:
    FV_SPYM = FV_SPY * ( SPYM_price / SPY_price )

Optional:
- Bank SPX targets (JPM, GS, BofA, MS, Citi) as manual benchmarks.
  If provided, we compute:
    - FV_Street (from bank targets)
    - FV_Blend  (mix of Market FV and Street FV)

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

# Major global benchmarks to show on the globe
GLOBAL_MARKETS = [
    {"name": "US · SPX", "ticker": "^GSPC", "lat": 40.7128, "lng": -74.0060},     # New York
    {"name": "UK · FTSE 100", "ticker": "^FTSE", "lat": 51.5074, "lng": -0.1278}, # London
    {"name": "EU · Euro Stoxx 50", "ticker": "^STOXX50E", "lat": 48.8566, "lng": 2.3522},  # Paris
    {"name": "JP · Nikkei 225", "ticker": "^N225", "lat": 35.6895, "lng": 139.6917},       # Tokyo
    {"name": "HK · Hang Seng", "ticker": "^HSI", "lat": 22.3193, "lng": 114.1694},         # Hong Kong
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

    /* Top metrics cards: use Streamlit columns + custom text classes */
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

    if is_undervalued:
        factor = 1.0 - pct / 100.0
    else:
        factor = 1.0 + pct / 100.0

    if factor == 0:
        raise ValueError("Factor became zero; check your inputs.")

    return price / factor


def street_fair_values_for_etf(etf_price: float, spx_price: float, bank_targets: dict) -> dict:
    """
    Map each bank's SPX target into ETF fair value using ETF/SPX ratio:

        k = ETF_now / SPX_now
        FV_bank(ETF) = k * SPX_target_bank
    """
    if spx_price <= 0:
        raise ValueError("SPX price must be positive.")

    k = etf_price / spx_price
    fv_by_bank = {}
    for bank, target in bank_targets.items():
        fv_by_bank[bank] = k * float(target)
    return fv_by_bank


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


@st.cache_data(ttl=300)
def get_global_index_changes(markets):
    """
    Get 1-day % change for each global benchmark in GLOBAL_MARKETS.
    Falls back to 0.0 if data is missing.
    """
    results = []
    for m in markets:
        change = 0.0
        try:
            hist = yf.Ticker(m["ticker"]).history(period="2d")
            if len(hist) >= 2:
                prev_close = hist["Close"].iloc[-2]
                last_close = hist["Close"].iloc[-1]
                if prev_close > 0:
                    change = (last_close - prev_close) / prev_close * 100.0
        except Exception:
            change = 0.0
        result = {
            "name": m["name"],
            "lat": m["lat"],
            "lng": m["lng"],
            "change": float(change),
        }
        results.append(result)
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
    st.sidebar.subheader("Bank SPX Targets")
    for name in BANK_NAMES:
        val = st.sidebar.text_input(
            f"{name} Target",
            value="",
            help="Leave blank to ignore this bank.",
        )
        if val.strip():
            try:
                bank_targets[name] = float(val.strip())
            except ValueError:
                st.sidebar.warning(f"Invalid number for {name}; ignoring.")

    st.sidebar.markdown("---")
    W_MARKET = st.sidebar.slider(
        "Weight on Market Fair Value",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
        help="1.0 = trust your market valuation only. 0.0 = banks only."
    )
    W_BANKS = 1.0 - W_MARKET
else:
    bank_targets = {}
    W_MARKET = 1.0
    W_BANKS = 0.0

show_banks = bool(bank_targets)


# -------------------------------
# MAIN: TITLE + CAPTION
# -------------------------------
st.title("FAIR VALUE DASHBOARD · SPY (BASE) & SPYM")
st.caption(
    "SPY fair value is derived directly from your market valuation input. "
    "SPYM fair value is scaled off SPY via the live SPYM/SPY price ratio. "
    "Bank SPX targets (if entered) are treated as benchmarks."
)

# -------------------------------
# LIVE DATA FETCH
# -------------------------------
try:
    spx_price = get_last_price(SPX_TICKER)
    spy_price = get_last_price(SPY_TICKER)
    spym_price = get_last_price(SPYM_TICKER)
except Exception as e:
    st.error(f"Error fetching data: {e}")
    st.stop()

# Compute SPY fair value from market input
fv_spy_market = calc_fair_value_from_market(spy_price, is_undervalued, market_pct)

# Derive SPYM fair value via price ratio to SPY
fv_spym_market = fv_spy_market * (spym_price / spy_price)


# -------------------------------
# TOP METRICS ROW
# -------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="metric-title">Market Condition</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metric-value">{market_state.upper()} {market_pct:.2f}%</div>',
        unsafe_allow_html=True,
    )

with col2:
    st.markdown('<div class="metric-title">SPX (LIVE)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metric-value">{spx_price:,.2f}</div>',
        unsafe_allow_html=True,
    )

with col3:
    if show_banks:
        st.markdown('<div class="metric-title">Blend Weights (Market / Banks)</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">{W_MARKET:.2f} / {W_BANKS:.2f}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="metric-title">Bank Benchmarks</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="metric-value">OFF</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# -------------------------------
# GLOBAL MARKETS ROTATING GLOBE
# -------------------------------
st.subheader("GLOBAL MARKETS · ROTATING GLOBE (BETA)")

try:
    globe_points = get_global_index_changes(GLOBAL_MARKETS)
    # Round changes for cleaner labels and avoid NaN in JS
    globe_data = [
        {
            "name": p["name"],
            "lat": p["lat"],
            "lng": p["lng"],
            "change": round(p["change"], 2),
        }
        for p in globe_points
    ]
    data_json = json.dumps(globe_data)

    globe_html = f"""
    <div id="globeViz"></div>
    <script src="https://unpkg.com/globe.gl"></script>
    <script>
    const data = {data_json};

    const world = Globe()
      (document.getElementById('globeViz'))
      .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')
      .backgroundColor('#050608')
      .showAtmosphere(true)
      .atmosphereColor('#ff9f1c')
      .atmosphereAltitude(0.25)
      .pointsData(data)
      .pointLat('lat')
      .pointLng('lng')
      .pointAltitude(d => 0.03 + Math.min(Math.abs(d.change) / 100 * 0.15, 0.3))
      .pointRadius(0.6)
      .pointColor(d => d.change >= 0 ? '#08ff7e' : '#ff4d4d')
      .pointLabel(d => `${{d.name}}: ${{d.change.toFixed(2)}}%`);

    world.controls().autoRotate = true;
    world.controls().autoRotateSpeed = 0.4;
    world.pointOfView({{ lat: 20, lng: 0, altitude: 2.0 }}, 4000);
    </script>
    <style>
    #globeViz {{
      width: 100%;
      height: 420px;
      margin-top: 8px;
      border-radius: 18px;
      border: 1px solid #ff9f1c33;
    }}
    </style>
    """

    components.html(globe_html, height=460)
except Exception as e:
    st.info(f"Global globe view unavailable right now: {e}")

st.markdown("---")

# -------------------------------
# BUILD TABLE FOR SPY & SPYM
# -------------------------------
rows = []

for ticker, price, fv_mkt in [
    (SPY_TICKER, spy_price, fv_spy_market),
    (SPYM_TICKER, spym_price, fv_spym_market),
]:
    row = {
        "Ticker": ticker,
        "Price": price,
        "FV_Market": fv_mkt,
        "Ups_M%": (fv_mkt - price) / price * 100.0,
    }

    if show_banks:
        fv_by_bank = street_fair_values_for_etf(price, spx_price, bank_targets)
        fv_street_avg = mean(fv_by_bank.values())
        ups_street = (fv_street_avg - price) / price * 100.0

        fv_blend = W_MARKET * fv_mkt + W_BANKS * fv_street_avg
        ups_blend = (fv_blend - price) / price * 100.0

        row["FV_Street"] = fv_street_avg
        row["Ups_S%"] = ups_street
        row["FV_Blend"] = fv_blend
        row["Ups_B%"] = ups_blend

    rows.append(row)

df = pd.DataFrame(rows)

if show_banks:
    df = df[
        [
            "Ticker",
            "Price",
            "FV_Market",
            "Ups_M%",
            "FV_Street",
            "Ups_S%",
            "FV_Blend",
            "Ups_B%",
        ]
    ]
else:
    df = df[
        [
            "Ticker",
            "Price",
            "FV_Market",
            "Ups_M%",
        ]
    ]


# Format + Bloomberg-style color on upsides
if show_banks:
    styled = (
        df.style
        .format(
            {
                "Price": "{:,.2f}",
                "FV_Market": "{:,.2f}",
                "Ups_M%": "{:,.2f}",
                "FV_Street": "{:,.2f}",
                "Ups_S%": "{:,.2f}",
                "FV_Blend": "{:,.2f}",
                "Ups_B%": "{:,.2f}",
            }
        )
        .applymap(color_upsides, subset=["Ups_M%", "Ups_S%", "Ups_B%"])
    )
else:
    styled = (
        df.style
        .format(
            {
                "Price": "{:,.2f}",
                "FV_Market": "{:,.2f}",
                "Ups_M%": "{:,.2f}",
            }
        )
        .applymap(color_upsides, subset=["Ups_M%"])
    )

st.subheader("FAIR VALUE SNAPSHOT (LIVE)")
st.dataframe(
    styled,
    use_container_width=True,
    height=220,
)

st.markdown(
    """
**Notes**

- **FV_Market**: Fair value from your UNDERVALUE / OVERVALUED input.  
  SPY is calculated directly; SPYM is scaled from SPY via the live SPYM/SPY price ratio.

- **Ups_M%**: (FV_Market − Price) / Price × 100.

- If bank targets are used:
  - **FV_Street**: Average ETF-level fair value implied by the bank SPX targets.
  - **FV_Blend**: W_MARKET × FV_Market + W_BANKS × FV_Street.
  - **Ups_S% / Ups_B%**: Upside vs current price using Street and Blended fair values.
"""
)
