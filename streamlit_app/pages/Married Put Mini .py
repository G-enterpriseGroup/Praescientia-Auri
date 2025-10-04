import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Configure Streamlit for mobile responsiveness
st.set_page_config(page_title="Married Put", layout="wide")

# Apply compact mobile-friendly CSS
st.markdown("""
    <style>
    /* Make dataframe tables responsive and compact */
    .stDataFrame, .stTable {
        overflow-x: auto;
        width: 100%;
    }
    [data-testid="stDataFrame"] table {
        font-size: 12px !important;
        white-space: nowrap !important;
    }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
        padding: 2px 6px !important;
    }
    [data-testid="stDataFrame"] th {
        font-weight: 600 !important;
    }
    /* Reduce Streamlit padding for mobile view */
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


def format_number(x):
    """Format numbers to remove unnecessary trailing zeros while keeping up to 2 decimals."""
    if isinstance(x, (int, float)):
        return f"{x:.2f}".rstrip('0').rstrip('.')
    return x


def calculate_max_loss(stock_price, options_table):
    """Calculate Max Loss for each option using both Ask and Last prices."""
    number_of_shares = 100  # Standard contract size

    # Perform calculations using the Ask Price
    options_table['Cost of Put (Ask)'] = options_table['Ask'] * number_of_shares
    options_table['Max Loss (Ask)'] = (
        (options_table['Strike'] * number_of_shares)
        - (stock_price * number_of_shares + options_table['Cost of Put (Ask)'])
    )
    options_table['Max Loss Calc (Ask)'] = options_table.apply(
        lambda row: f"({format_number(row['Strike'])} × {number_of_shares}) - ({format_number(stock_price * number_of_shares)} + {format_number(row['Cost of Put (Ask)'])})",
        axis=1
    )

    # Perform calculations using the Last Price
    options_table['Cost of Put (Last)'] = options_table['Last Price'] * number_of_shares
    options_table['Max Loss (Last)'] = (
        (options_table['Strike'] * number_of_shares)
        - (stock_price * number_of_shares + options_table['Cost of Put (Last)'])
    )
    o
