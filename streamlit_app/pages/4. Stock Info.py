import streamlit as st
import yfinance as yf
import pandas as pd

# App title
st.title('Enhanced Stock Information and Financials App')

# User input
ticker_symbol = st.text_input("Enter the stock ticker:", "AAPL")

# Fetch stock information
stock_info = yf.Ticker(ticker_symbol)

# Basic information
st.write(f"**Company Name:** {stock_info.info.get('longName', 'N/A')}")
st.write("**Sector:**", stock_info.info.get('sector', 'N/A'))
st.write("**Full Time Employees:**", stock_info.info.get('fullTimeEmployees', 'N/A'))
st.write("**Business Summary:**", stock_info.info.get('longBusinessSummary', 'N/A'))

# Stock statistics with expanded information
st.subheader("Expanded Stock Statistics")
statistics_keys = [
    'marketCap', 'forwardPE', 'dividendYield', 'profitMargins', 
    'beta', 'trailingEPS', 'priceToSalesTrailing12Months', 'priceToBook'
]
for key in statistics_keys:
    st.write(f"**{key.replace('_', ' ').title()}:** {stock_info.info.get(key, 'N/A')}")

# Financials with yearly and quarterly views
st.subheader("Financials")
financials_yearly = stock_info.financials
financials_quarterly = stock_info.quarterly_financials
tab1, tab2 = st.tabs(["Yearly Financials", "Quarterly Financials"])
with tab1:
    st.dataframe(financials_yearly)
with tab2:
    st.dataframe(financials_quarterly)

# Balance Sheet with yearly and quarterly views
st.subheader("Balance Sheet")
balance_sheet_yearly = stock_info.balance_sheet
balance_sheet_quarterly = stock_info.quarterly_balance_sheet
tab3, tab4 = st.tabs(["Yearly Balance Sheet", "Quarterly Balance Sheet"])
with tab3:
    st.dataframe(balance_sheet_yearly)
with tab4:
    st.dataframe(balance_sheet_quarterly)

#______________________________________________
