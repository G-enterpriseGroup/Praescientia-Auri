
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

# Improved organization by grouping imports and removing duplicates

st.set_page_config(layout="wide")

def hide_streamlit_branding():
    """Hide Streamlit's default branding"""
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

hide_streamlit_branding()

st.write("# Forecasting Stock - Designed & Implemented by Raj Ghotra")

# Function to calculate the start and end date, improved to be more concise
def calculate_date(days, start=True):
    current_date = datetime.today()
    delta_days = 0
    while delta_days < days:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:  # Monday to Friday
            delta_days += 1
    return current_date

default_start_date = calculate_date(395)
default_end_date = calculate_date(30, start=False)

# Using concise variables and ensuring code readability
SN = st.slider('Seasonality', 7, 30, 22)
EMA_values = {f'EMA{i}': st.slider(f'EMA{i}', 0, 100, default) for i, default in zip([12, 26, 9], [13, 39, 9])}
split_percentage = st.slider('Training set proportion %', 0.2, 0.99, 0.80)
Ticker = st.text_input('Ticker', value="SPY")
start_date1 = st.date_input('Start Date', value=default_start_date)
end_date1 = st.date_input('End Date', value=default_end_date)

st.write(f'Days Predicting: 30\nSeasonality: {SN}\n' + '\n'.join([f'{k}: {v}' for k, v in EMA_values.items()]) +
         f'\nTicker: {Ticker}\nStart Date: {start_date1}\nEnd Date: {end_date1}\nTraining set proportion %: {split_percentage}')

if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...Estimated 4 Minutes'):
        progress_bar = st.progress(0)
        df = yf.Ticker(Ticker).history(period="max")
        df = df.loc[pd.to_datetime(start_date1).tz_localize('America/New_York'):pd.to_datetime(end_date1).tz_localize('America/New_York')]
        # Before trying to localize the timezone, check if the index is already timezone-aware
        if df.index.tz is None:
            df.index = pd.to_datetime(df.index).tz_localize('America/New_York')
        else:
            df.index = pd.to_datetime(df.index).tz_convert('America/New_York')
        # Removing unnecessary columns in one line
        df = df[['Close']].copy()
        progress_bar.progress(10)

        # EMA calculation using a loop
        for ema, value in EMA_values.items():
            df[ema] = df['Close'].ewm(span=value, adjust=False).mean()

        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # ARIMA model optimization and fitting
        C = df["Close"].dropna()
        progress_bar.progress(30)

        auto_model = auto_arima(C, trace=True, suppress_warnings=True)
        progress_bar.progress(60)

        arima_order = auto_model.order
        seasonal_order = (arima_order[0], arima_order[1], arima_order[2], SN)

        model = SARIMAX(C, order=arima_order, seasonal_order=seasonal_order).fit()
        progress_bar.progress(80)

        # Predictions
        predictions = model.predict(start=len(C), end=len(C) + 30)
        progress_bar.progress(90)

        # Visualization improvements for clarity
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['Close'], label='Actual Close')
        plt.plot(predictions.index, predictions, label='Forecast', linestyle='--')
        plt.title(f'{Ticker} Stock Price Forecast')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.tight_layout()
        
        st.pyplot(plt)
        progress_bar.progress(100)
        st.success("Model run successfully!")
