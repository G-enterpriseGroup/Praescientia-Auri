import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# Title of the app
st.title("Historical Stock and ETF Data Downloader")

# Input for the stock ticker
ticker = st.text_input("Enter the Ticker Symbol (e.g., AAPL, SPY):")

# Date selection
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", value=datetime(2020, 1, 1))
with col2:
    end_date = st.date_input("End Date", value=datetime.today())

# Button to download data
if st.button("Download Data"):
    if ticker:
        try:
            # Fetching data from Yahoo Finance
            data = yf.download(ticker, start=start_date, end=end_date)
            
            # Checking if data is retrieved
            if not data.empty:
                # Creating a CSV for download
                csv = data.to_csv().encode('utf-8')
                
                # Download button
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{ticker}.csv",
                    mime="text/csv"
                )
                st.success(f"Data for {ticker} downloaded successfully!")
            else:
                st.error("No data found for the selected ticker and date range. Please check your inputs.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a valid ticker symbol.")
