
import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def get_stock_data(tickers, start_date, end_date):
    data = {}
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        data[ticker] = hist
    return data

def plot_stock_data(data):
    fig, axes = plt.subplots(4, 2, figsize=(15, 10))
    axes = axes.flatten()

    for i, (ticker, hist) in enumerate(data.items()):
        ax = axes[i]
        hist['Close'].plot(ax=ax)
        ax.set_title(f"{ticker} - APY: {hist['Dividends'].sum() * 100:.2f}%")
        ax.set_ylabel('Price')
        ax.set_xlabel('Date')

    plt.tight_layout()
    st.pyplot(fig)

st.title("Multi-Function Charts with Dividend Yield (APY)")

tickers_input = st.text_area("Tickers Entry Box (separated by commas)", "AAPL, MSFT, GOOG")
start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")
past_days = st.number_input("Or past days from today", min_value=0, value=90)

tickers = [ticker.strip() for ticker in tickers_input.split(",")]

if past_days > 0:
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.Timedelta(days=past_days)

if st.button("Generate Charts"):
    data = get_stock_data(tickers, start_date, end_date)
    plot_stock_data(data)
