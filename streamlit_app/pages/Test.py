import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import requests
from lxml import html
import math

# Set Streamlit to always run in wide mode
st.set_page_config(layout="wide")

def get_stock_data(tickers, past_days):
    data = {}
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.Timedelta(days=past_days)
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        data[ticker] = hist
    return data

def get_dividend_info(ticker):
    urls = [
        f"https://stockanalysis.com/etf/{ticker}/dividend/",
        f"https://stockanalysis.com/stocks/{ticker}/dividend/"
    ]
    for url in urls:
        response = requests.get(url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            dividend_xpath = '/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div'
            apy_xpath = '/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[1]/div'
            dividend = tree.xpath(dividend_xpath)
            apy = tree.xpath(apy_xpath)
            if dividend and apy:
                return dividend[0].text_content(), apy[0].text_content()
    return "N/A", "N/A"

def plot_stock_data(data):
    num_tickers = len(data)
    num_rows = math.ceil(num_tickers / 2)  # Always 2 columns
    fig, axes = plt.subplots(num_rows, 2, figsize=(25, 5 * num_rows), dpi=400)
    axes = axes.flatten()

    for i, (ticker, hist) in enumerate(data.items()):
        ax = axes[i]
        hist['Close'].plot(ax=ax)
        annual_dividend, apy = get_dividend_info(ticker)
        ax.set_title(f"{ticker} - Annual Dividend: {annual_dividend}, APY: {apy}", fontsize=14, fontweight='bold')
        ax.set_ylabel('Price', fontsize=12)
        ax.set_xlabel('Date', fontsize=12)

    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    st.pyplot(fig)

st.title("Multi-Function Charts with Dividend Yield (Annual Dividend and APY)")

tickers_input = st.text_area("Tickers Entry Box (separated by commas)", "AAPL, MSFT, GOOG")
past_days = st.number_input("Past days from today", min_value=1, value=90)

tickers = [ticker.strip() for ticker in tickers_input.split(",")]

if st.button("Generate Charts"):
    data = get_stock_data(tickers, past_days)
    plot_stock_data(data)
