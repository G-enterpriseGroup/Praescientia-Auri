import streamlit as st
import yfinance as yf

# Title of the app
st.title('Stock Information App')

# User input for the stock ticker
ticker_symbol = st.text_input("Enter the stock ticker:", "AAPL")

# Fetching the stock information
stock_info = yf.Ticker(ticker_symbol)

# Displaying the company name
st.write(f"**Company Name:** {stock_info.info['longName']}")

# Displaying other relevant information
st.write("**Sector:**", stock_info.info['sector'])
st.write("**Full Time Employees:**", stock_info.info['fullTimeEmployees'])
st.write("**Business Summary:**", stock_info.info['longBusinessSummary'])

# Running the app: `streamlit run your_script_name.py`
