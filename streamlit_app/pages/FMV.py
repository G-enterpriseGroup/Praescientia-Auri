import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def fetch_historical_data(ticker, days):
    stock = yf.Ticker(ticker)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    hist = stock.history(start=start_date, end=end_date)
    
    # Calculate the average closing price
    average_price = hist['Close'].mean()
    
    return {
        "Ticker": ticker,
        "Average Price ({} days)".format(days): average_price
    }

def calculate_average_prices(tickers, days):
    historical_data = []
    for ticker in tickers:
        data = fetch_historical_data(ticker, days)
        historical_data.append(data)
    
    df = pd.DataFrame(historical_data)
    return df

# Streamlit app
st.title("Average Stock Price Over Specified Days")

# Input for tickers
tickers_input = st.text_input("Enter stock tickers separated by commas:", "AAPL,MSFT,GOOGL")
tickers = [ticker.strip() for ticker in tickers_input.split(',')]

# Input for number of days
days_input = st.number_input("Enter the number of days to calculate the average price:", min_value=1, value=30)

if st.button("Calculate Average Prices"):
    average_prices_df = calculate_average_prices(tickers, days_input)
    st.dataframe(average_prices_df)
