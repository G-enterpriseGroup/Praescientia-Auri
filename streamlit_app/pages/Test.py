import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup

def get_stock_data(tickers, past_days):
    data = {}
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.Timedelta(days=past_days)
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        data[ticker] = hist
    return data

def fetch_dividend_info(ticker):
    etf_url = f"https://stockanalysis.com/etf/{ticker}/dividend/"
    stock_url = f"https://stockanalysis.com/stocks/{ticker}/dividend/"
    
    response = requests.get(etf_url)
    if response.status_code != 200:
        response = requests.get(stock_url)
        if response.status_code != 200:
            return None
        
    soup = BeautifulSoup(response.content, 'html.parser')
    dividend_info = soup.select_one("div[class^='Dividend']").get_text(strip=True)
    return dividend_info

def calculate_apy(hist):
    dividends = hist['Dividends'].sum()
    initial_price = hist['Close'].iloc[0]
    apy = (dividends / initial_price) * 100  # APY as a percentage
    return apy

def plot_stock_data(data):
    num_stocks = len(data)
    num_cols = 2
    num_rows = (num_stocks + num_cols - 1) // num_cols  # Calculate the number of rows needed

    fig, axes = plt.subplots(num_rows, num_cols, figsize=(20, num_rows * 5))  # Increase figsize for larger plots
    axes = axes.flatten()

    for i, (ticker, hist) in enumerate(data.items()):
        ax = axes[i]
        hist['Close'].plot(ax=ax)
        apy = calculate_apy(hist)
        dividend_info = fetch_dividend_info(ticker)
        ax.set_title(f"{ticker} - APY: {apy:.2f}%\n{dividend_info}")
        ax.set_ylabel('Price')
        ax.set_xlabel('Date')

    for j in range(i+1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    st.pyplot(fig)

st.title("Multi-Function Charts with Dividend Yield (APY)")

tickers_input = st.text_area("Tickers Entry Box (separated by commas)", "AAPL, MSFT, GOOG")
past_days = st.number_input("Past days from today", min_value=1, value=90)

tickers = [ticker.strip() for ticker in tickers_input.split(",")]

if st.button("Generate Charts"):
    data = get_stock_data(tickers, past_days)
    plot_stock_data(data)
