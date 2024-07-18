import streamlit as st
import pandas as pd
import requests
from lxml import html
import yfinance as yf

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    
    try:
        response = requests.get(etf_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            price = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
        else:
            response = requests.get(stock_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                price = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
            else:
                price = "N/A"
    except:
        price = "N/A"
    
    # Get yield percentage from yfinance
    try:
        stock_info = yf.Ticker(ticker)
        div_yield = stock_info.info.get('dividendYield', 0) * 100
    except:
        div_yield = "N/A"
    
    return {"Ticker": ticker, "Price": price, "Yield %": div_yield}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(data)
    
    # Display DataFrame with custom width and height
    st.dataframe(df, width=1200, height=600)
