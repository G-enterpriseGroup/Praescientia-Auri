import streamlit as st
import pandas as pd
import requests
from lxml import html
import yfinance as yf
from datetime import datetime, timedelta

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    
    try:
        response = requests.get(etf_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0]
            yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0]
            annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
            ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0]
            frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0]
            dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0]
            return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
        else:
            response = requests.get(stock_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0]
                yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0]
                annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
                ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0]
                frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0]
                dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0]
                return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
            else:
                return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}
    except:
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

# Function to get returns for a given ticker and periods
def get_returns(ticker):
    stock = yf.Ticker(ticker)
    end_date = datetime.today()
    start_dates = {
        "1d": end_date - timedelta(days=1),
        "5d": end_date - timedelta(days=5),
        "1mo": end_date.replace(day=1) - relativedelta.relativedelta(months=1),
        "3mo": end_date.replace(day=1) - relativedelta.relativedelta(months=3),
        "6mo": end_date.replace(day=1) - relativedelta.relativedelta(months=6),
        "ytd": datetime(end_date.year, 1, 1),
        "1y": end_date - timedelta(days=365),
        "5y": end_date - timedelta(days=365*5),
        "max": datetime(1900, 1, 1)
    }
    
    returns = {}
    for period, start_date in start_dates.items():
        data = stock.history(start=start_date, end=end_date)
        if not data.empty:
            start_price = data['Close'].iloc[0]
            end_price = data['Close'].iloc[-1]
            returns[period] = f"{(((end_price - start_price) / start_price) * 100):.2f}%"
        else:
            returns[period] = "N/A"
    
    return returns

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    stock_data_list = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    returns_data_list = [get_returns(ticker.strip()) for ticker in tickers if ticker.strip()]
    
    for stock_data, returns_data in zip(stock_data_list, returns_data_list):
        stock_data.update(returns_data)
    
    df = pd.DataFrame(stock_data_list)
    
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
        table-layout: auto !important.
    }
    </style>
    """,
    unsafe_allow_html=True,
)
