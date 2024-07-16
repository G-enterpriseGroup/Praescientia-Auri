import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def get_stock_data(tickers, past_days):
    data = {}
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.Timedelta(days=past_days)
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        data[ticker] = hist
    return data

def calculate_apy(hist):
    dividends = hist['Dividends'].sum()
    initial_price = hist['Close'].iloc[0]
    if initial_price != 0:
        apy = (dividends / initial_price) * 100  # APY as a percentage
    else:
        apy = 0
    return apy

def plot_stock_data(data):
    fig, axes = plt.subplots(4, 2, figsize=(15, 10))
    axes = axes.flatten()

    for i, (ticker, hist) in enumerate(data.items()):
        if i >= 8:
            break
        ax = axes[i]
        hist['Close'].plot(ax=ax)
        apy = calculate_apy(hist)
        
        # Debugging information
        st.write(f"Ticker: {ticker}")
        st.write(f"Initial Price: {hist['Close'].iloc[0]}")
        st.write(f"Total Dividends: {hist['Dividends'].sum()}")
        st.write(f"Calculated APY: {apy:.2f}%")
        
        ax.set_title(f"{ticker} - APY: {apy:.2f}%")
        ax.set_ylabel('Price')
        ax.set_xlabel('Date')

    for j in range(i + 1, 8):
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
