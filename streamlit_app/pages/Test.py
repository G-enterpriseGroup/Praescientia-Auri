import streamlit as st
import yfinance as yf
import pandas as pd

def get_dividend_dates_prices(ticker):
    # Fetch stock data including dividends
    stock = yf.Ticker(ticker)
    history = stock.history(period="5y")
    dividends = stock.dividends

    # Filter the history to only include the ex-dividend dates
    ex_dividend_prices = history[history.index.isin(dividends.index)]

    # Calculate the difference between high and low prices on ex-dividend dates
    ex_dividend_prices['Difference'] = ex_dividend_prices['High'] - ex_dividend_prices['Low']

    # Select only the necessary columns
    result = ex_dividend_prices[['Open', 'High', 'Low', 'Difference']]
    return result

st.title('Stock Price Analysis on Ex-Dividend Dates')

# Input ticker
ticker = st.text_input('Enter ticker symbol:', 'PULS')

if ticker:
    # Display data
    try:
        dividend_data = get_dividend_dates_prices(ticker)
        st.write(dividend_data)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
