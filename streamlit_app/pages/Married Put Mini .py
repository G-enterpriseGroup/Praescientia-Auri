import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Set Streamlit page configuration
st.set_page_config(page_title="Married Put Terminal", layout="wide", page_icon="📉")

# =========================
# EXTREME BLOOMBERG / ORANGE THEME (CSS)
# =========================
st.markdown(
    """
    <style>
    /* Global background + font */
    html, body, [class*="stApp"] {
        background-color: #050608;
        color: #ffb347;
        font-family: "Menlo", "Consolas", "Roboto Mono", monospace;
        font-weight: 700;
    }

    .main {
        background-color: #050608;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #050608;
        border-right: 1px solid #ff9f1c66;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {
        color: #ffb347;
        font-weight: 700;
    }

    /* Titles */
    h1, h2, h3, h4 {
        color: #ffb347;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    /* Metric labels + values */
    .metric-title {
        font-size: 0.8rem;
        color: #ff9f1c;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 900;
        color: #ffb347;
    }

    /* Buttons */
    button[kind="primary"], button[data-baseweb="button"] {
        background-color: #ff9f1c !important;
        color: #050608 !important;
        border: 1px solid #ffb347 !important;
        border-radius: 2px !important;
        font-weight: 900 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    button[kind="primary"]:hover, button[data-baseweb="button"]:hover {
        background-color: #ffb347 !important;
        color: #050608 !important;
    }

    /* Text & number inputs */
    .stTextInput > div > div > input,
    .stNumberInput input {
        background-color: #050608 !important;
        color: #ffb347 !important;
        border-radius: 0px !important;
        border: 1px solid #ff9f1caa !important;
        font-weight: 700 !important;
    }
    .stTextInput label, .stNumberInput label {
        color: #ffb347 !important;
        font-weight: 800 !important;
    }

    /* Dataframe styling */
    table {
        border-collapse: collapse !important;
    }
    thead tr {
        background-color: #15191f !important;
        border-bottom: 1px solid #ff9f1ccc !important;
    }
    thead th {
        color: #ffb347 !important;
        font-weight: 900 !important;
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
        color: #ffb347 !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: #101317 !important;
        color: #ffb347 !important;
        border: 1px solid #ff9f1caa !important;
        border-radius: 2px !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .stDownloadButton > button:hover {
        background-color: #15191f !important;
        color: #ffffff !important;
    }

    /* Alerts */
    .stAlert {
        border-radius: 0px !important;
        border: 1px solid #ff9f1caa !important;
        font-weight: 700 !important;
    }
    .stAlert p {
        color: #ffb347 !important;
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def calculate_max_loss(stock_price, options_table):
    """
    Calculate Max Loss for each option using both Ask Price and Last Price:
    Max Loss = (Strike Price × 100) - (Cost of Stock + Cost of Put)
    """
    number_of_shares = 100  # Standard contract size

    # Perform calculations using the Ask Price
    options_table['CPA'] = (options_table['ASK'] * number_of_shares)
    options_table['MLA'] = (
        (options_table['STK'] * number_of_shares) -
        (stock_price * number_of_shares + options_table['CPA'])
    )

    # Perform calculations using the Last Price
    options_table['CPL'] = (options_table['LP'] * number_of_shares)
    options_table['MLL'] = (
        (options_table['STK'] * number_of_shares) -
        (stock_price * number_of_shares + options_table['CPL'])
    )

    return options_table

def calculate_days_left(expiration_date):
    """Calculate the total number of calendar days left until the expiration date."""
    today = datetime.today()
    expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
    return (expiration_date - today).days

def display_put_options_all_dates(ticker_symbol, stock_price):
    try:
        ticker = yf.Ticker(ticker_symbol)
        expiration_dates = ticker.options
        if not expiration_dates:
            st.error(f"No options data available for ticker {ticker_symbol}.")
            return

        all_data = pd.DataFrame()

        for chosen_date in expiration_dates:
            days_left = calculate_days_left(chosen_date)
            st.markdown(f"### EXPIRATION: {chosen_date}  ·  {days_left} DAYS LEFT")

            # Fetch put options
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                st.warning(f"No puts available for expiration date {chosen_date}.")
                continue

            # Prepare full put options table (for calculations)
            puts_table = puts[[
                "contractSymbol",
                "strike",
                "lastPrice",
                "bid",
                "ask",
                "volume",
                "openInterest",
                "impliedVolatility"
            ]]
            puts_table.columns = ["CN", "STK", "LP", "BID", "ASK", "VOL", "OI", "IV"]
            puts_table["EXP"] = chosen_date

            # Run max loss calculation
            puts_table = calculate_max_loss(stock_price, puts_table)

            # Display version (hide contract + quote details)
            display_table = puts_table.drop(
                columns=["CN", "LP", "BID", "ASK", "VOL", "OI", "IV", "EXP"]
            )
            display_table = display_table.reset_index(drop=True)

            # Collect everything for CSV
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # Format numeric columns with no decimals
            num_cols = [c for c in ["STK", "CPA", "MLA", "CPL", "MLL"] if c in display_table.columns]
            styled_table = (
                display_table
                .style
                .format({col: "{:,.0f}".format for col in num_cols})  # no decimals
                .highlight_max(subset=["MLA", "MLL"], color="#ff9f1c55")
            )

            st.dataframe(styled_table, use_container_width=True, height=280)

        if not all_data.empty:
            csv = all_data.to_csv(index=False)
            st.download_button(
                label="Download All Expiration Data as CSV",
                data=csv,
                file_name=f"{ticker_symbol}_put_options.csv",
                mime="text/csv",
            )
        else:
            st.warning(f"No put options data to display or download for {ticker_symbol}.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

def main():
    st.title("MARRIED PUT · OPTIONS TERMINAL")

    # Top row: Ticker + company + last price
    col_ticker, col_info = st.columns([1, 3])

    with col_ticker:
        ticker_symbol = st.text_input(
            "TICKER",
            "",
            placeholder="e.g. SPY",
        ).upper().strip()

    long_name = "N/A"
    current_price = 0.0

    if ticker_symbol:
        try:
            ticker = yf.Ticker(ticker_symbol)
            long_name = ticker.info.get("longName", "N/A")
            stock_info = ticker.history(period="1d")
            current_price = stock_info["Close"].iloc[-1] if not stock_info.empty else 0.0
        except Exception:
            long_name = "N/A"
            current_price = 0.0

    with col_info:
        st.markdown('<div class="metric-title">UNDERLYING</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">{ticker_symbol or "--"}  ·  {long_name}</div>',
            unsafe_allow_html=True,
        )

    if not ticker_symbol:
        st.warning("ENTER A VALID TICKER SYMBOL TO BEGIN.")
        return

    # Row for current price & user-defined purchase price
    col_price1, col_price2 = st.columns(2)
    with col_price1:
        st.markdown('<div class="metric-title">LAST CLOSE</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">{current_price:,.2f}</div>',
            unsafe_allow_html=True,
        )

    with col_price2:
        stock_price = st.number_input(
            "PURCHASE PRICE / SHARE",
            min_value=0.0,
            value=float(current_price),
            step=0.01,
            help="Stock price you paid (or plan to pay) for the married put.",
        )

    if stock_price <= 0:
        st.warning("PLEASE ENTER A VALID STOCK PRICE.")
        return

    st.markdown("---")

    # Action row
    col_btn, col_note = st.columns([1, 3])
    with col_btn:
        fetch = st.button("FETCH PUT CHAINS")

    with col_note:
        st.caption(
            "Max Loss (MLA/MLL) = (Strike × 100) − (Stock Cost + Put Premium). "
            "MLA uses ASK, MLL uses LAST."
        )

    if fetch:
        display_put_options_all_dates(ticker_symbol, stock_price)

if __name__ == "__main__":
    main()
