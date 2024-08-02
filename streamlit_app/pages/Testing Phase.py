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
            price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0].strip()
            yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0].strip()
            annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0].strip()
            ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0].strip()
            frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0].strip()
            dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0].strip()
            return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
        else:
            response = requests.get(stock_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0].strip()
                yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0].strip()
                annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0].strip()
                ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0].strip()
                frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0].strip()
                dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0].strip()
                return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
            else:
                return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}
    except Exception as e:
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

# Function to calculate stock performance
def calculate_performance(ticker):
    stock = yf.Ticker(ticker)
    today = datetime.now()
    periods = {
        "1 day": today - timedelta(days=1),
        "5 days": today - timedelta(days=5),
        "1 month": today - timedelta(days=30),
        "6 months": today - timedelta(days=182),
        "Year to date": datetime(today.year, 1, 1),
        "1 year": today - timedelta(days=365),
        "5 years": today - timedelta(days=1825)
    }
    
    performance = {}
    for period_name, start_date in periods.items():
        try:
            hist = stock.history(start=start_date, end=today)
            if not hist.empty:
                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                performance[period_name] = ((end_price - start_price) / start_price) * 100
            else:
                performance[period_name] = "N/A"
        except Exception as e:
            performance[period_name] = "N/A"
    return performance

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    performance_data = [calculate_performance(ticker.strip()) for ticker in tickers if ticker.strip()]

    for i in range(len(data)):
        data[i].update(performance_data[i])

    columns = ["Ticker", "Price", "Yield %", "Annual Dividend", "Ex Dividend Date", "Frequency", "Dividend Growth %", 
               "1 day", "5 days", "1 month", "6 months", "Year to date", "1 year", "5 years"]

    df = pd.DataFrame(data, columns=columns)

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
