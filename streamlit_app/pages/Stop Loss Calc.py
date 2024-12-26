import streamlit as st
import yfinance as yf

# Function to calculate ATR
def calculate_atr(data, period=14):
    high_low = data['High'] - data['Low']
    high_close = abs(data['High'] - data['Close'].shift(1))
    low_close = abs(data['Low'] - data['Close'].shift(1))
    tr = high_low.combine(high_close, max).combine(low_close, max)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1]

# Streamlit app
st.title('Stop Loss Calculator Based on ATR')

# Input: Ticker symbol
ticker = st.text_input('Enter the stock ticker:', 'AAPL').upper()

# Fetch stock data
if ticker:
    try:
        data = yf.download(ticker, period='1y', interval='1d')
        if not data.empty:
            # Current price
            current_price = data['Close'].iloc[-1]
            
            # ATR calculation
            atr = calculate_atr(data)
            
            # Lowest price in the last 14 days
            last_14_day_low = data['Low'].tail(14).min()
            
            # Stop loss calculation
            stop_loss = last_14_day_low - atr
            
            # Output results
            st.write(f"**Current Price:** ${current_price:.2f}")
            st.write(f"**ATR (14 days):** ${atr:.2f}")
            st.write(f"**14-Day Lowest Low:** ${last_14_day_low:.2f}")
            st.write(f"**Stop Loss Level:** ${stop_loss:.2f}")
        else:
            st.error("No data found for the ticker. Please check the symbol and try again.")
    except Exception as e:
        st.error(f"An error occurred: {e}")
