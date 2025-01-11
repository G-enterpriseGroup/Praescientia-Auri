import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

# Title of the app
st.title("Historical Stock and ETF Data Downloader with Trailing Stop Calculator")

# Input for the stock ticker
ticker = st.text_input("Enter the Ticker Symbol (e.g., AAPL, SPY):")

# Check if ticker is valid when the user presses Enter
if ticker:
    try:
        # Attempt to fetch data to verify ticker
        test_data = yf.Ticker(ticker).info
        if test_data:
            st.success(f"Ticker '{ticker}' has been found.")
        else:
            st.error(f"Ticker '{ticker}' could not be found. Please check the symbol.")
    except Exception:
        st.error(f"Ticker '{ticker}' could not be found. Please check the symbol.")

# Initialize session state for selected dates
if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.today() - timedelta(days=365)
if "end_date" not in st.session_state:
    st.session_state.end_date = datetime.today()

# Interval preset buttons
st.subheader("Select Date Range Preset:")

# Buttons for preset intervals
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
manual_start_date = st.date_input(
    "Start Date", value=st.session_state.start_date, key="manual_start_date"
)
manual_end_date = st.date_input(
    "End Date", value=st.session_state.end_date, key="manual_end_date"
)

# Update session state with manual date input
st.session_state.start_date = manual_start_date
st.session_state.end_date = manual_end_date

# Button to download data and calculate trailing stop
if st.button("Download Data and Calculate Trailing Stop"):
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

                # Calculate trailing stop percentage
                data['Daily_Range_Percent'] = (
                    (data['High'] - data['Low']) / data['Low']
                ) * 100
                average_range_percent = data['Daily_Range_Percent'].mean()
                std_dev_range_percent = data['Daily_Range_Percent'].std()
                optimal_trailing_stop = average_range_percent + std_dev_range_percent

                # Display trailing stop calculation
                st.subheader("Trailing Stop Calculation")
                st.write(f"**Average Daily Range (%):** {average_range_percent:.2f}%")
                st.write(f"**Standard Deviation (%):** {std_dev_range_percent:.2f}%")
                st.write(
                    f"**Optimal Trailing Stop (%):** {optimal_trailing_stop:.2f}%"
                )
                
                # Detailed proof and explanation
                st.subheader("Calculation Breakdown and Explanation")
                st.markdown("""
                ### How Calculations Are Done:
                1. **Daily Range Percent**: Calculated as  
                   `((High - Low) / Low) * 100`  
                   This provides the percentage range of price movement within each trading day.
                2. **Average Daily Range**:  
                   This is the **mean** of all the daily range percentages for the given time period.  
                   Formula: `Mean(Daily_Range_Percent)`.
                3. **Standard Deviation**:  
                   Measures the **volatility** of the daily range percentages.  
                   Formula: `Std(Daily_Range_Percent)`.
                4. **Optimal Trailing Stop**:  
                   Combines the **average daily range** with the **standard deviation** to account for typical daily movements and market volatility.  
                   Formula: `Average Daily Range + Standard Deviation`.

                ### Why This Matters:
                - The **Average Daily Range** tells us the typical price fluctuation, helping to set a baseline for the stop-loss order.
                - The **Standard Deviation** accounts for price volatility, ensuring the stop-loss isn't triggered prematurely during normal price swings.
                - The **Optimal Trailing Stop** provides a balance between minimizing losses and staying in the trade during regular price fluctuations.

                ### Example:
                If a stock has:
                - Daily high of $105 and low of $100,  
                  The Daily Range = `(105 - 100) / 100 * 100 = 5%`.
                - Over time, if the average daily range is **1.37%** and standard deviation is **0.63%**,  
                  The Optimal Trailing Stop = `1.37% + 0.63% = 2.00%`.
                """)

            else:
                st.error(
                    "No data found for the selected ticker and date range. Please check your inputs."
                )
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a valid ticker symbol.")
