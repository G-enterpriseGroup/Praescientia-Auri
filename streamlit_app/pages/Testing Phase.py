import streamlit as st
import yfinance as yf
import pandas as pd

# Function to get historical data for a given ticker and period
def get_historical_data(ticker, period):
    stock = yf.Ticker(ticker)
    data = stock.history(period=period)
    return data

# Function to calculate percentage change
def calculate_percentage_change(data):
    if not data.empty:
        return (data['Close'][-1] / data['Close'][0] - 1) * 100
    return None

# Function to display stock data for multiple periods
def display_stock_data(ticker):
    periods = {
        "5 Days": "5d",
        "1 Month": "1mo",
        "3 Months": "3mo",
        "YTD": "ytd",
        "1 Year": "1y",
        "5 Years": "5y",
        "Max": "max"
    }
    
    st.header(f"Stock Performance for {ticker}")

    data = []
    for period_name, period_code in periods.items():
        historical_data = get_historical_data(ticker, period_code)
        percentage_change = calculate_percentage_change(historical_data)
        data.append([period_name, f"{percentage_change:.2f}%" if percentage_change is not None else "N/A"])

    df = pd.DataFrame(data, columns=["Period", "Percentage Change"])
    st.table(df)

# Streamlit app layout
st.title("Stock Performance Viewer")

ticker = st.text_input("Enter Ticker Symbol:", "AAPL")

if ticker:
    display_stock_data(ticker)
