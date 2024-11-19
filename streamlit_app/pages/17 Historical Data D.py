import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Title of the app
st.title("Historical Stock and ETF Data Downloader with Trailing Stop Visualization")

# Input for the stock ticker
ticker = st.text_input("Enter the Ticker Symbol (e.g., AAPL, SPY):")

# Initialize session state for selected dates
if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.today() - timedelta(days=365)
if "end_date" not in st.session_state:
    st.session_state.end_date = datetime.today()

# Interval preset buttons
st.subheader("Select Date Range Preset:")
if st.button("1 Month"):
    st.session_state.start_date = datetime.today() - timedelta(days=30)
    st.session_state.end_date = datetime.today()
if st.button("3 Months"):
    st.session_state.start_date = datetime.today() - timedelta(days=90)
    st.session_state.end_date = datetime.today()
if st.button("6 Months"):
    st.session_state.start_date = datetime.today() - timedelta(days=180)
    st.session_state.end_date = datetime.today()
if st.button("1 Year"):
    st.session_state.start_date = datetime.today() - timedelta(days=365)
    st.session_state.end_date = datetime.today()

# Manual date input
st.subheader("Or Modify the Dates:")
manual_start_date = st.date_input("Start Date", value=st.session_state.start_date)
manual_end_date = st.date_input("End Date", value=st.session_state.end_date)

# Update session state with manual date input
st.session_state.start_date = manual_start_date
st.session_state.end_date = manual_end_date

# Button to download data and visualize trailing stop
if st.button("Download Data and Visualize Trailing Stop"):
    if ticker:
        try:
            # Fetching data from Yahoo Finance
            data = yf.download(
                ticker,
                start=st.session_state.start_date,
                end=st.session_state.end_date,
            )
            
            # Check if data is retrieved
            if data.empty:
                st.error("No data found for the selected ticker and date range. Please check your inputs.")
            else:
                # Ensure required columns exist
                required_columns = {'High', 'Low', 'Close'}
                if not required_columns.issubset(data.columns):
                    st.error(f"The dataset is missing required columns: {required_columns - set(data.columns)}")
                else:
                    # Handle missing data
                    data.dropna(subset=['High', 'Low', 'Close'], inplace=True)

                    # Calculate trailing stop percentage
                    data['Daily_Range_Percent'] = (
                        (data['High'] - data['Low']) / data['Low']
                    ) * 100
                    average_range_percent = data['Daily_Range_Percent'].mean()
                    std_dev_range_percent = data['Daily_Range_Percent'].std()
                    optimal_trailing_stop = average_range_percent + std_dev_range_percent

                    # Calculate trailing stop value
                    max_close_price = data['Close'].max()
                    trailing_stop_value = max_close_price * (1 - optimal_trailing_stop / 100)

                    # Display results
                    st.subheader("Trailing Stop Calculation")
                    st.write(f"**Average Daily Range (%):** {average_range_percent:.2f}%")
                    st.write(f"**Standard Deviation (%):** {std_dev_range_percent:.2f}%")
                    st.write(f"**Optimal Trailing Stop (%):** {optimal_trailing_stop:.2f}%")
                    st.write(f"**Trailing Stop Value:** ${trailing_stop_value:.2f}")

                    # Visualize data
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(data['Close'], label="Close Price", color="blue")
                    ax.axhline(
                        y=trailing_stop_value,
                        color="red",
                        linestyle="--",
                        label=f"Trailing Stop (${trailing_stop_value:.2f})"
                    )
                    ax.set_title(f"{ticker} Stock Price with Trailing Stop")
                    ax.set_xlabel("Date")
                    ax.set_ylabel("Price")
                    ax.legend()
                    st.pyplot(fig)

                    # Allow data download
                    csv = data.to_csv().encode("utf-8")
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{ticker}.csv",
                        mime="text/csv",
                    )
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a valid ticker symbol.")
