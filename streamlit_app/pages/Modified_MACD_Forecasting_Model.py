import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Title
st.title('Financial Data Forecasting')

# Inputs
ticker = st.text_input('Enter Ticker Symbol', 'AAPL')
start_date = st.date_input('Select Start Date', value=pd.to_datetime('2020-01-01'))
short_window = st.slider('Short EMA Window', 12, 5, 50, 1)
long_window = st.slider('Long EMA Window', 26, 10, 60, 1)

if st.button('Forecast Data'):
    # Fetch Data
    data = yf.download(ticker, start=start_date)
    data = data['Close'].asfreq('D').fillna(method='ffill')  # Ensure daily frequency & fill missing values
    
    # Calculate MACD
    exp1 = data.ewm(span=short_window, adjust=False).mean()
    exp2 = data.ewm(span=long_window, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=9, adjust=False).mean()

    # Plot MACD and Signal Line
    plt.figure(figsize=(10, 6))
    plt.plot(macd, label='MACD', color='blue')
    plt.plot(signal_line, label='Signal Line', color='red')
    plt.legend(loc='upper left')
    st.pyplot(plt)

    # Model Training and Forecasting
    model = SARIMAX(macd, order=(0, 1, 1), seasonal_order=(1, 1, 1, 12))
    result = model.fit(disp=False)
    
    # Forecast
    forecast = result.forecast(steps=30)
    forecast_dates = pd.date_range(data.index[-1] + pd.Timedelta(days=1), periods=30)

    # Plot Forecast
    plt.figure(figsize=(10, 6))
    plt.plot(macd.index, macd, label='MACD', color='blue')
    plt.plot(forecast_dates, forecast, label='Forecast', color='green')
    plt.legend(loc='upper left')
    st.pyplot(plt)
