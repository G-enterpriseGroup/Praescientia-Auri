import streamlit as st
import yfinance as yf
import pandas as pd

# Function to get historical data for a given ticker and period
def get_historical_data(ticker, period):
    stock = yf.Ticker(ticker)
    return stock.history(period=period)

# Function to display stock data for multiple periods
def display_stock_data(ticker):
    periods = {
        "5 Days": "5d",
        "1 Month": "1mo",
        "3 Months": "3mo",
        "YTD": "ytd",
        "1 Year": "1y",
        "5 Years": "5y",
        "Max": "max"
    }
    
    st.header(f"Stock data for {ticker}")
    
    for period_name, period_code in periods.items():
        st.subheader(period_name)
        data = get_historical_data(ticker, period_code)
        st.line_chart(data['Close'])
        st.write(data)

# Streamlit app layout
st.title("Stock Performance Viewer")

ticker = st.text_input("Enter Ticker Symbol:", "AAPL")

if ticker:
    display_stock_data(ticker)
