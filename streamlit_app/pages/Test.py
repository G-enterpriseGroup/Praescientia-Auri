import yfinance as yf
import streamlit as st
import pandas as pd

# Title for the Streamlit app
st.title('Historical Stock Price Viewer')

# Inputs for ticker symbol and date range
ticker = st.text_input('Enter ticker symbol:', 'PULS')
start_date = st.date_input('Start date', pd.to_datetime('2023-04-01'))
end_date = st.date_input('End date', pd.to_datetime('today'))

# Function to fetch historical stock data
def get_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    return data[['High', 'Low']]

# Button to trigger data load
if st.button('Show Historical Prices'):
    data = get_data(ticker, start_date, end_date)
    if not data.empty:
        st.write(f"Displaying high and low prices for {ticker}")
        st.dataframe(data)
    else:
        st.write("No data found for the given ticker and date range.")

