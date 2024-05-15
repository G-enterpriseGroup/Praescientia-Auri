import streamlit as st
import yfinance as yf
import pandas as pd

def get_first_trading_day_prices(ticker):
    # Fetch historical data
    data = yf.download(ticker, start="2020-01-01")

    # Resample to get the first trading day of each month
    monthly_data = data.resample('MS').first()

    # Calculate the difference between the high and low prices
    monthly_data['Difference'] = monthly_data['High'] - monthly_data['Low']

    # Select only the necessary columns
    result = monthly_data[['Open', 'High', 'Low', 'Difference']]
    return result

st.title('PULS: First Trading Day Prices for Each Month')

# Input ticker
ticker = st.text_input('Enter ticker symbol:', 'PULS')

if ticker:
    # Display data
    try:
        prices_data = get_first_trading_day_prices(ticker)
        st.write(prices_data)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
