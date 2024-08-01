import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend"

    try:
        response = requests.get(etf_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
        else:
            response = requests.get(stock_url)
            if response.status_code != 200:
                return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A",
                        "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

        price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0]
        yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0]
        annual_dividend = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[2]/div/text()')[0]
        ex_dividend_date = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[3]/div/text()')[0]
        frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0]
        dividend_growth = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[6]/div/text()')[0]

        return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend,
                "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}

    except Exception as e:
        print(f"An error occurred while fetching data for {ticker}: {e}")
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A",
                "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

# Function to get additional stock data
def get_additional_stock_data(ticker):
    url = f"https://www.tradingview.com/symbols/{ticker}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            data = {}

            timeframes = ["1 Day", "5 Days", "1 Month", "6 Months", "YTD", "1 Year", "5 Year", "All Time"]
            for timeframe in timeframes:
                xpath_string = f'//span[contains(text(), "{timeframe}")]/ancestor::button//span[@class="MuiButton-label"]/span[2]'
                data_value = tree.xpath(xpath_string)
                value = data_value[0].text if data_value else "N/A"
                data[timeframe] = value

            return data
        else:
            return {timeframe: "N/A" for timeframe in timeframes}

    except Exception as e:
        print(f"An error occurred while fetching additional data for {ticker}: {e}")
        return {timeframe: "N/A" for timeframe in timeframes}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    stock_data = []
    additional_data = []

    for ticker in tickers:
        stock_data.append(get_stock_data(ticker.strip()))
        additional_data.append(get_additional_stock_data(ticker.strip()))

    stock_df = pd.DataFrame(stock_data)
    additional_df = pd.DataFrame(additional_data)

    result_df = pd.concat([stock_df, additional_df], axis=1)

    # Display DataFrame
    st.write(result_df)

# Adjust the width and height of the page and ensure table fits the data
st.markdown("""
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
    }
    </style>
    """, unsafe_allow_html=True)
