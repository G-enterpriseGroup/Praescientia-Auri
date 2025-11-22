import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Set Streamlit page configuration
st.set_page_config(page_title="Married Put Terminal", layout="wide", page_icon="📉")

# =========================
# BLOOMBERG-STYLE THEME (CSS)
# =========================
st.markdown(
    """
    <style>
    /* Global background + font */
    html, body, [class*="stApp"] {
        background-color: #050608;
        color: #f4f4f4;
        font-family: "Menlo", "Consolas", "Roboto Mono", monospace;
    }

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

    /* Titles */
    h1, h2, h3, h4 {
        color: #ffb347;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* Metrics-like labels */
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

    /* Buttons */
    button[kind="primary"], button[data-baseweb="button"] {
        background-color: #ff9f1c !important;
        color: #050608 !important;
        border: 1px solid #ffb347 !important;
        border-radius: 2px !important;
        font-weight: 700 !important;
    }
    button[kind="primary"]:hover, button[data-baseweb="button"]:hover {
        background-color: #ffb347 !important;
        color: #050608 !important;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stNumberInput input {
        background-color: #050608 !important;
        color: #f4f4f4 !important;
        border-radius: 0px !important;
        border: 1px solid #444 !important;
    }

    /* Dataframe styling */
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

    /* Download button */
    .stDownloadButton > button {
        background-color: #22252b !important;
        color: #ffb347 !important;
        border: 1px solid #ff9f1c88 !important;
        border-radius: 2px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton > button:hover {
        background-color: #2c3139 !important;
        color: #ffffff !important;
    }

    /* Warnings / errors tweaks */
    .stAlert {
        border-radius: 0px !important;
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
        ticker = yf.Ticker(ticker
