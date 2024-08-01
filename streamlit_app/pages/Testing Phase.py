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

# Function to get exact historical data for a given ticker and date
def get_exact_historical_data(ticker, date):
    stock = yf.Ticker(ticker)
    data = stock.history(start=date, end=(date + timedelta(days=1)))
    if not data.empty:
        return data['Close'].iloc[0]
    return None

# Function to calculate percentage change between two dates
def calculate_exact_percentage_change(ticker, start_date, end_date):
    start_price = get_exact_historical_data(ticker, start_date)
    end_price = get_exact_historical_data(ticker, end_date)
    if start_price is not None and end_price is not None:
        return (end_price / start_price - 1) * 100
    return None

# Function to get stock performance data
def get_stock_performance_data(ticker):
    today = datetime.today()
    periods = {
        "5 Days": today - timedelta(days=5),
        "1 Month": today - timedelta(days=30),
        "3 Months": today - timedelta(days=90),
        "6 Months": today - timedelta(days=180),
        "YTD": datetime(today.year, 1, 1),
        "1 Year": today - timedelta(days=365),
        "5 Years": today - timedelta(days=1825),
        "Max": datetime(1900, 1, 1)
    }
    
    data = {}
    for period_name, start_date in periods.items():
        percentage_change = calculate_exact_percentage_change(ticker, start_date, today)
        data[period_name] = f"{percentage_change:.2f}%" if percentage_change is not None else "N/A"

    return data

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    stock_data_list = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    performance_data_list = [get_stock_performance_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    
    for stock_data, performance_data in zip(stock_data_list, performance_data_list):
        stock_data.update(performance_data)
    
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
        table-layout: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
