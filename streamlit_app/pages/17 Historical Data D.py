import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Title of the app
st.title("Stock Data Downloader with Trailing Stop Loss Calculator")

# Input for the stock ticker
ticker = st.text_input("Enter the Ticker Symbol (e.g., AAPL, SPY):")

# Initialize session state for selected dates
if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.today() - timedelta(days=365)
if "end_date" not in st.session_state:
    st.session_state.end_date = datetime.today()

# Date range selection
st.subheader("Select or Modify Date Range:")
manual_start_date = st.date_input(
    "Start Date", value=st.session_state.start_date, key="manual_start_date"
)
manual_end_date = st.date_input(
    "End Date", value=st.session_state.end_date, key="manual_end_date"
)

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

            if not data.empty:
                # Create a downloadable CSV file
                csv = data.to_csv().encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{ticker}.csv",
                    mime="text/csv",
                )
                st.success(f"Data for {ticker} downloaded successfully!")

                # Step-by-step trailing stop loss calculation
                st.subheader("Step-by-Step Trailing Stop Loss Calculation")

                # 1. Calculate Daily Range
                data["Daily_Range"] = data["High"] - data["Low"]
                st.write("**Daily Range Calculation (High - Low):**")
                st.write(data[["High", "Low", "Daily_Range"]].dropna())

                # 2. Calculate Daily Range Percent
                data["Daily_Range_Percent"] = (data["Daily_Range"] / data["Low"]) * 100
                st.write("**Daily Range Percent Calculation:**")
                st.write(data[["Daily_Range", "Low", "Daily_Range_Percent"]].dropna())

                # 3. Average Daily Range %
                average_range_percent = data["Daily_Range_Percent"].mean()
                st.write(f"**Average Daily Range (%):** {average_range_percent:.2f}%")

                # 4. Standard Deviation of Daily Range %
                std_dev_range_percent = data["Daily_Range_Percent"].std()
                st.write(f"**Standard Deviation of Daily Range (%):** {std_dev_range_percent:.2f}%")

                # 5. Calculate True Range (TR)
                data["TR"] = np.maximum(
                    data["High"] - data["Low"], 
                    np.maximum(abs(data["High"] - data["Close"].shift(1)), abs(data["Low"] - data["Close"].shift(1)))
                )
                st.write("**True Range (TR) Calculation:**")
                st.write(data[["High", "Low", "Close", "TR"]].dropna())

                # 6. Calculate ATR (Average True Range)
                data["ATR"] = data["TR"].rolling(window=14).mean()
                st.write("**Average True Range (ATR):**")
                st.write(data[["TR", "ATR"]].dropna())

                # 7. ATR-Based Trailing Stop %
                last_close = data["Close"].iloc[-1]
                last_atr = data["ATR"].iloc[-1]
                atr_trailing_stop_percent = (last_atr / last_close) * 100
                st.write(f"**ATR-Based Trailing Stop (%):** {atr_trailing_stop_percent:.2f}%")

                # 8. Optimal Trailing Stop %
                optimal_trailing_stop_percent = average_range_percent + std_dev_range_percent
                st.write(f"**Optimal Trailing Stop (%):** {optimal_trailing_stop_percent:.2f}%")

                # Visualization of Trailing Stop
                st.subheader("Trailing Stop Visualization")
                data["Trailing_Stop"] = data["Close"] * (1 - optimal_trailing_stop_percent / 100)
                
                plt.figure(figsize=(10, 6))
                plt.plot(data["Close"], label="Close Price", color="blue")
                plt.plot(data["Trailing_Stop"], label="Trailing Stop", color="red", linestyle="--")
                plt.title(f"Trailing Stop Loss for {ticker}")
                plt.legend()
                plt.xlabel("Date")
                plt.ylabel("Price")
                st.pyplot(plt)

            else:
                st.error("No data found for the selected ticker and date range. Please try again.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a valid ticker symbol.")
