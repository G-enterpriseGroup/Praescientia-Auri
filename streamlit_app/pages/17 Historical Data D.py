import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Title of the app
st.title("Historical Stock Data Downloader with Trailing Stop Visualization")

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
                progress=False,
            )

            # Check if data is retrieved
            if data.empty:
                st.error("No data found for the selected ticker and date range. Please check your inputs.")
            else:
                # Ensure the Close column exists
                if 'Close' not in data.columns:
                    st.error("The dataset is missing the 'Close' column.")
                else:
                    # Calculate trailing stop percentage
                    max_close_price = data['Close'].max()
                    min_close_price = data['Close'].min()
                    average_range_percent = ((max_close_price - min_close_price) / min_close_price) * 100
                    std_dev_range_percent = data['Close'].pct_change().std() * 100
                    optimal_trailing_stop = average_range_percent + std_dev_range_percent

                    # Calculate trailing stop value
                    trailing_stop_value = max_close_price * (1 - optimal_trailing_stop / 100)

                    # Display results
                    st.subheader("Trailing Stop Calculation")
                    st.write(f"**Average Close Range (%):** {average_range_percent:.2f}%")
                    st.write(f"**Standard Deviation of Close Changes (%):** {std_dev_range_percent:.2f}%")
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
                    csv = data[['Close']].to_csv().encode("utf-8")
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{ticker}_Close.csv",
                        mime="text/csv",
                    )
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a valid ticker symbol.")
