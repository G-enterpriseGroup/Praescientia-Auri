import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data (limited to necessary data)
def get_additional_stock_data(ticker):
    base_url = f"https://www.tradingview.com/symbols/{ticker}/"
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            # General method for finding text next to labels
            performance = {
                "1 Day": tree.xpath('//*[contains(text(), "1 day")]/following-sibling::*[1]/text()')[0].strip(),
                "5 Days": tree.xpath('//*[contains(text(), "5 days")]/following-sibling::*[1]/text()')[0].strip(),
                "1 Month": tree.xpath('//*[contains(text(), "1 month")]/following-sibling::*[1]/text()')[0].strip(),
                "6 Months": tree.xpath('//*[contains(text(), "6 months")]/following-sibling::*[1]/text()')[0].strip(),
                "1 Year": tree.xpath('//*[contains(text(), "1 year")]/following-sibling::*[1]/text()')[0].strip(),
                "5 Years": tree.xpath('//*[contains(text(), "5 years")]/following-sibling::*[1]/text()')[0].strip(),
                "All Time": tree.xpath('//*[contains(text(), "All time")]/following-sibling::*[1]/text()')[0].strip(),
            }
            return performance
        else:
            return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Months": "N/A", "1 Year": "N/A", "5 Years": "N/A", "All Time": "N/A"}
    except Exception as e:
        return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Months": "N/A", "1 Year": "N/A", "5 Years": "N/A", "All Time": "N/A"}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch additional data for each ticker
if tickers:
    additional_data = [get_additional_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(additional_data, columns=["1 Day", "5 Days", "1 Month", "6 Months", "1 Year", "5 Years", "All Time"])

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
