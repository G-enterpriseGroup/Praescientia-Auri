import streamlit as st
import yfinance as yf
import pandas as pd

# Function to calculate ATR
def calculate_atr(df, period=14):
    df['High-Low'] = df['High'] - df['Low']
    df['High-Close'] = abs(df['High'] - df['Close'].shift(1))
    df['Low-Close'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['High-Low', 'High-Close', 'Low-Close']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()
    return df['ATR'].iloc[-1]

# Streamlit interface
st.title('Stop Loss Calculator Based on ATR')

# Input for ticker symbol
ticker = st.text_input('Enter the stock ticker:', 'AAPL')

# Fetch the stock data
data = yf.download(ticker, period='1y', interval='1d')

if not data.empty:
    # Calculate the ATR
    latest_atr = calculate_atr(data)

    # Get the low of the last 14 days
    last_14_day_low = data['Low'].tail(14).min()

    # Calculate the stop loss
    stop_loss = last_14_day_low - latest_atr

    st.write(f"Latest ATR: {latest_atr:.2f}")
    st.write(f"Lowest Low of Last 14 Days: {last_14_day_low:.2f}")
    st.write(f"Stop Loss: {stop_loss:.2f}")
else:
    st.write("No data found. Please enter a valid ticker symbol.")
