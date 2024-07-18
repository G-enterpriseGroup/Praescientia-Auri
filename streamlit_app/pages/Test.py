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
        dividend_info = fetch_dividend_info(ticker
