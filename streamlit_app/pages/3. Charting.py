
import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima
import plotly.graph_objects as go
from pandas.tseries.holiday import USFederalHolidayCalendar

import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
from datetime import datetime, timedelta

# Function to fetch stock data
def fetch_data(ticker, interval, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
    return data

# Streamlit UI
st.title('Stock Analysis App')

# Input: Stock ticker
ticker = st.text_input('Enter Stock Ticker (e.g., AAPL):').upper()

# Dropdown for time intervals
interval = st.selectbox('Select Time Interval:', ('1d', '5d', '1mo', '3mo', '6mo', '1y'))

# Calculate start date based on selected interval
end_date = datetime.today()
if interval == '1d':
    start_date = end_date - timedelta(days=1)
elif interval == '5d':
    start_date = end_date - timedelta(days=7)
elif interval == '1mo':
    start_date = end_date - timedelta(days=30)
elif interval == '3mo':
    start_date = end_date - timedelta(days=90)
elif interval == '6mo':
    start_date = end_date - timedelta(days=180)
else: # '1y'
    start_date = end_date - timedelta(days=365)

if ticker:
    # Fetch data
    df = fetch_data(ticker, '1d', start_date, end_date)
    
    # Display next earnings date
    stock_info = yf.Ticker(ticker)
    earnings_date = stock_info.calendar.loc['Earnings Date'][0] if not stock_info.calendar.empty else "Not Available"
    st.write(f"Next Earnings Date: {earnings_date}")
    
    # Plotly candlestick chart
    fig = go.Figure(data=[go.Candlestick(x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'])])
    
    fig.update_layout(title=f'{ticker} Candlestick Chart', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig)
    
    # For pattern recognition, implement specific pattern analysis here
    # This requires further development based on pattern analysis algorithms or indicators


#_______________________________________________________________________________________________________________________________________________________________
