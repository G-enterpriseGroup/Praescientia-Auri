import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"

# Function to get additional stock data
def get_additional_stock_data(ticker):
    base_url = f"https://www.tradingview.com/symbols/{ticker}/"
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            # General method for finding text next to labels
            performance = {}
            labels = tree.xpath('//span[contains(text(), "day") or contains(text(), "month") or contains(text(), "year") or contains(text(), "time") or contains(text(), "5 days")]/text()')
            values = tree.xpath('//span[contains(@class, "change")]/text()')
            for label, value in zip(labels, values):
                performance[label] = value.strip()
            return performance
        else:
            return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}
    except Exception as e:
        return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(data, columns=["Ticker", "Price", "Yield %", "Annual Dividend", "Ex Dividend Date", "Frequency", "Dividend Growth %"])

    # Get additional data for each ticker
    additional_data = [get_additional_stock_data(ticker) for ticker in df["Ticker"]]
    additional_df = pd.DataFrame(additional_data)

    # Combine main data and additional data
    df = pd.concat([df, additional_df], axis=1)

    # Display DataFrame
    st.write(df)

# Adjust the width and height of the page and ensure table fits the data
st.markdown(
    """
    <style>
    .reportview-container .main .block-container{
        max-width: 100%;
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
    table {
        width: 100% !important;
        height: 100% !important;
        table-layout: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
