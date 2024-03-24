import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# Title of the app
st.title("Stock Chart and Candlestick Pattern Detection")

# Sidebar for user inputs
ticker = st.sidebar.text_input("Enter Stock Ticker", value='AAPL').upper()
interval = st.sidebar.selectbox("Select Interval", ['1h', '1d'])

# Fetching stock data
data = yf.download(ticker, period="1mo", interval=interval)

# Displaying stock chart
fig = go.Figure(data=[go.Candlestick(x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'])])

fig.update_layout(title=f"{ticker} Stock Chart", xaxis_title="Date", yaxis_title="Price")
st.plotly_chart(fig)

# Basic pattern detection (Example: Doji)
doji_threshold = 0.1  # Threshold to consider a candlestick a Doji
data['Doji'] = (abs(data['Open'] - data['Close']) <= (data['High'] - data['Low']) * doji_threshold)

if data['Doji'].any():
    st.write("Doji pattern detected in the selected time frame.")
else:
    st.write("No Doji pattern detected in the selected time frame.")

# Note: Extend the pattern detection logic for other patterns as required.
