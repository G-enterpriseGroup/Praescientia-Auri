
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import streamlit as st
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima
from sklearn.metrics import mean_squared_error
from math import sqrt

# Set Streamlit page config
st.set_page_config(layout="wide")

# Hide Streamlit branding
st.markdown('''
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
''', unsafe_allow_html=True)

# Streamlit app title
st.write("# Stock Forecasting - Designed & Implemented by Raj Ghotra")

# Input widgets for model parameters
SN = st.slider('Seasonality', min_value=7, max_value=30, value=22, step=1)
split_percentage = st.slider('Training set proportion %', min_value=0.2, max_value=0.8, value=0.8, step=0.05)
Ticker = st.text_input('Ticker', value="SPY").upper()

# Displaying the model parameters
st.write(f"Seasonality: {SN}, Ticker: {Ticker}, Training set proportion %: {split_percentage*100}")

# Function to calculate start and end dates
def calculate_start_end_dates(days):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

# Fetching stock data
def fetch_stock_data(ticker, start_date, end_date):
    df = yf.download(ticker, start=start_date, end=end_date)
    return df

# Running the forecasting model
if st.button('Run Forecasting Model'):
    with st.spinner('Model is running...'):
        start_date, end_date = calculate_start_end_dates(365 * 2) # Last 2 years
        df = fetch_stock_data(Ticker, start_date, end_date)

        # Splitting the dataset
        split_point = int(len(df) * split_percentage)
        train, test = df['Close'][:split_point], df['Close'][split_point:]

        # Model fitting
        stepwise_model = auto_arima(train, start_p=1, start_q=1, max_p=3, max_q=3, m=SN, start_P=0, seasonal=True, d=1, D=1, trace=True, error_action='ignore', suppress_warnings=True)
        model = SARIMAX(train, order=stepwise_model.order, seasonal_order=stepwise_model.seasonal_order)
        model_fit = model.fit(disp=False)

        # Forecast
        forecast = model_fit.forecast(steps=len(test))
        
        # Evaluation
        mse = mean_squared_error(test, forecast)
        rmse = sqrt(mse)

        # Plotting results
        plt.figure(figsize=(10, 6))
        plt.plot(train.index, train, label='Train')
        plt.plot(test.index, test, label='Test')
        plt.plot(forecast.index, forecast, label='Forecast')
        plt.legend()
        plt.title('Stock Price Forecasting')
        st.pyplot(plt)
        
        st.write(f"RMSE: {rmse:.2f}")

# Displaying a note
st.write("Model accuracy is influenced by the selected parameters and the inherent predictability of the stock market.")
