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

    # Calculate the percentage difference
    percent_difference = ((last_14_day_low - stop_loss) / last_14_day_low) * 100

    st.write(f"Latest ATR: {latest_atr:.2f}")
    st.write(f"Lowest Low of Last 14 Days: {last_14_day_low:.2f}")
    st.write(f"Stop Loss: {stop_loss:.2f}")
    st.write(f"Percentage Difference: {percent_difference:.2f}%")
    
    # Note description
    st.write("**Note:** The percentage difference indicates how much below the lowest price in the last 14 days the stop loss is set. A higher percentage means a more conservative stop loss.")
    
    # Calculation description
    st.write("""
        ### How the Calculation is Done:
        - **ATR Calculation:** The Average True Range (ATR) is calculated over the last 14 days. It measures market volatility by considering the range of price movements.
        - **Lowest Price in the Last 14 Days:** The application identifies the lowest price (low point) observed in the last 14 days of trading.
        - **Stop Loss Calculation:** The stop loss is set by subtracting the ATR from the lowest price in the last 14 days.
        - **Percentage Difference:** This shows how much below the last 14 days' low the stop loss is set, with a higher percentage indicating a more conservative stop loss.
    """)
    
else:
    st.write("No data found. Please enter a valid ticker symbol.")
