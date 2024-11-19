import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

# Title of the app
st.title("Historical Stock and ETF Data Downloader")

# Input for the stock ticker
ticker = st.text_input("Enter the Ticker Symbol (e.g., AAPL, SPY):")

# Interval preset buttons
st.subheader("Select Date Range Preset:")
col1, col2, col3, col4 = st.columns(4)

# Default dates
start_date = None
end_date = datetime.today()

# Interval buttons logic
if col1.button("1 Month"):
    start_date = end_date - timedelta(days=30)
elif col2.button("3 Months"):
    start_date = end_date - timedelta(days=90)
elif col3.button("6 Months"):
    start_date = end_date - timedelta(days=180)
elif col4.button("1 Year"):
    start_date = end_date - timedelta(days=365)

# Manual date input
st.subheader("Or Modify the Dates:")
manual_start_date = st.date_input("Start Date", value=start_date or datetime(2020, 1, 1))
manual_end_date = st.date_input("End Date", value=end_date)

# Apply manual date inputs if changed
if manual_start_date and manual_end_date:
    start_date = manual_start_date
    end_date = manual_end_date

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
