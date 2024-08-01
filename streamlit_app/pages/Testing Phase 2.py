import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    tradingview_url = f"https://www.tradingview.com/symbols/{ticker}/"

    # Initializing the stock data with default N/A values
    stock_data = {
        "Ticker": ticker,
        "Price": "N/A",
        "Yield %": "N/A",
        "Annual Dividend": "N/A",
        "Ex Dividend Date": "N/A",
        "Frequency": "N/A",
        "Dividend Growth %": "N/A",
        "1 Day": "N/A",
        "5 Days": "N/A",
        "1 Month": "N/A",
        "6 Month": "N/A",
        "YTD": "N/A",
        "1 Year": "N/A",
        "5 Year": "N/A",
        "All Time": "N/A"
    }

    try:
        response = requests.get(etf_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            stock_data.update({
                "Price": tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0],
                "Yield %": tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0],
                "Annual Dividend": tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0],
                "Ex Dividend Date": tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0],
                "Frequency": tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0],
                "Dividend Growth %": tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0],
            })
        else:
            response = requests.get(stock_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                stock_data.update({
                    "Price": tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0],
                    "Yield %": tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0],
                    "Annual Dividend": tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0],
                    "Ex Dividend Date": tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0],
                    "Frequency": tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0],
                    "Dividend Growth %": tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0],
                })
    except Exception as e:
        # Logging or handling exception if needed
        pass

    # Try to get performance data from TradingView
    try:
        response = requests.get(tradingview_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            stock_data.update({
                "1 Day": tree.xpath('//span[contains(text(), "1D")]/../following-sibling::span/text()')[0],
                "5 Days": tree.xpath('//span[contains(text(), "5D")]/../following-sibling::span/text()')[0],
                "1 Month": tree.xpath('//span[contains(text(), "1M")]/../following-sibling::span/text()')[0],
                "6 Month": tree.xpath('//span[contains(text(), "6M")]/../following-sibling::span/text()')[0],
                "YTD": tree.xpath('//span[contains(text(), "YTD")]/../following-sibling::span/text()')[0],
                "1 Year": tree.xpath('//span[contains(text(), "1Y")]/../following-sibling::span/text()')[0],
                "5 Year": tree.xpath('//span[contains(text(), "5Y")]/../following-sibling::span/text()')[0],
                "All Time": tree.xpath('//span[contains(text(), "All")]/../following-sibling::span/text()')[0],
            })
    except Exception as e:
        # Logging or handling exception if needed
        pass

    return stock_data

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(data)
    
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
