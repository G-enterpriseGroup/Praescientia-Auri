import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

# Title of the app
st.title("Historical Stock and ETF Data Downloader")

# Input for the stock ticker
ticker = st.text_input("Enter the Ticker Symbol (e.g., AAPL, SPY):")

# Initialize session state for selected dates
if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.today() - timedelta(days=365)
if "end_date" not in st.session_state:
    st.session_state.end_date = datetime.today()

# Interval preset buttons
st.subheader("Select Date Range Preset:")

# Buttons for preset intervals
preset_selected = False
if st.button("1 Month"):
    st.session_state.start_date = datetime.today() - timedelta(days=30)
    st.session_state.end_date = datetime.today()
    preset_selected = True
if st.button("3 Months"):
    st.session_state.start_date = datetime.today() - timedelta(days=90)
    st.session_state.end_date = datetime.today()
    preset_selected = True
if st.button("6 Months"):
    st.session_state.start_date = datetime.today() - timedelta(days=180)
    st.session_state.end_date = datetime.today()
    preset_selected = True
if st.button("1 Year"):
    st.session_state.start_date = datetime.today() - timedelta(days=365)
    st.session_state.end_date = datetime.today()
    preset_selected = True

# Manual date input
st.subheader("Or Modify the Dates:")
manual_start_date = st.date_input(
    "Start Date", value=st.session_state.start_date, key="manual_start_date"
)
manual_end_date = st.date_input(
    "End Date", value=st.session_state.end_date, key="manual_end_date"
)

# Update session state with manual date input
st.session_state.start_date = manual_start_date
st.session_state.end_date = manual_end_date

# Button to download data
if st.button("Download Data"):
    if ticker:
        try:
            # Fetching data from Yahoo Finance
            data = yf.download(
                ticker,
                start=st.session_state.start_date,
                end=st.session_state.end_date,
            )
            
            # Checking if data is retrieved
            if not data.empty:
                # Creating a CSV for download
                csv = data.to_csv().encode("utf-8")
                
                # Download button
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{ticker}.csv",
                    mime="text/csv",
                )
                st.success(f"Data for {ticker} downloaded successfully!")
            else:
                st.error("No data found for the selected ticker and date range. Please check your inputs.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a valid ticker symbol.")
