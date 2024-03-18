import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Function to fetch data
def fetch_stock_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    return data

# Streamlit app layout
st.title('30 Days Stock Price Candlestick Chart')

# User input for stock ticker
stock_ticker = st.text_input('Enter Stock Ticker:', 'AAPL').upper()

# Calculate dates for the last 30 business days
end_date = datetime.today()
start_date = end_date - timedelta(days=45) # Extend the days to ensure we cover 30 business days approximately

# Fetching the stock data
data = fetch_stock_data(stock_ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

# Check if data is empty
if not data.empty:
    # Create the candlestick chart
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'])])

    # Update layout for a better visual
    fig.update_layout(
        title=f'{stock_ticker} Stock Price',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        xaxis_rangeslider_visible=False, # Hide the range slider
        xaxis=dict(
            tickmode='array', # Use an array of custom tick values
            tickvals=data.index[::3], # Show every 3rd label to prevent overlap
            ticktext=[date.strftime('%Y-%m-%d') for date in data.index][::3] # Format date
        )
    )
    
    # Update layout to make it wider
    fig.update_layout(autosize=False, width=800, height=600)

    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No data available for the given ticker.")


import streamlit as st
from datetime import datetime, timedelta
import pyperclip

def calculate_business_days_ago(start_date, business_days):
    while business_days > 0:
        start_date -= timedelta(days=1)
        if start_date.weekday() < 5:  # Monday = 0, Sunday = 6
            business_days -= 1
    return start_date

# Display the app title
st.title('Date 30 Business Days Ago')

# Today's date
today = datetime.now()

# Calculate 30 business days ago
business_days_ago_date = calculate_business_days_ago(today, 30)

# Display the result
date_str = business_days_ago_date.strftime('%Y-%m-%d')

# Display the result for manual copy
st.text_input("Copy the date from here:", date_str, help="Select and copy this date manually.")





