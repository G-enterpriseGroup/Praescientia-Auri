import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Function to get stock performance
def get_stock_performance(ticker):
    try:
        stock = yf.Ticker(ticker)
        today = datetime.now().date()
        
        # Define the date ranges
        date_ranges = {
            "1 day": today - timedelta(days=1),
            "5 days": today - timedelta(days=5),
            "1 month": today - timedelta(days=30),
            "6 months": today - timedelta(days=182),
            "Year to date": datetime(today.year, 1, 1).date(),
            "1 year": today - timedelta(days=365),
            "5 years": today - timedelta(days=1825)
        }
        
        # Fetch historical data for the past 5 years
        data = stock.history(start=date_ranges["5 years"], end=today)
        
        # Calculate performance for each period
        performance = {}
        for period, start_date in date_ranges.items():
            try:
                start_price = data.loc[start_date]["Close"]
                end_price = data.iloc[-1]["Close"]
                performance[period] = ((end_price - start_price) / start_price) * 100
            except:
                performance[period] = "N/A"
        
        return {"Ticker": ticker, **performance}
    except Exception as e:
        return {"Ticker": ticker, "Error": str(e)}

# Streamlit App
st.title("Stock Performance Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_performance(ticker.strip()) for ticker in tickers if ticker.strip()]
    columns = ["Ticker", "1 day", "5 days", "1 month", "6 months", "Year to date", "1 year", "5 years"]
    df = pd.DataFrame(data, columns=columns)

    # Display DataFrame
    st.write(df)

# Adjust the width and height of the page and ensure table fits the data
st.markdown(
    """
    <style>
    .reportview-container .main .block-container{
        max-width: 100%;
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
    table {
        width: 100% !important;
        height: 100% !important;
        table-layout: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
