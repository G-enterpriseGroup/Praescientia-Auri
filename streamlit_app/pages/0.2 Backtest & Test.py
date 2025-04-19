import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX
import plotly.graph_objects as go
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import BDay
import warnings

# Attempt to import pmdarima; catch all exceptions to avoid C-extension load errors
try:
    from pmdarima import auto_arima
    PMDARIMA_AVAILABLE = True
except Exception as e:
    PMDARIMA_AVAILABLE = False
    warnings.warn(f"pmdarima unavailable ({e}); defaulting to ARIMA(1,1,1)")

# Streamlit page configuration
st.set_page_config(layout="wide")

# Hide Streamlit branding
def hide_streamlit_branding():
    st.markdown(
        '''
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
        ''', unsafe_allow_html=True
    )

hide_streamlit_branding()

# Title
st.write("# Forecasting & Visualization by Raj Ghotra")

# Utility: calculate most recent business date offset
def calculate_business_date(days_ago):
    date = datetime.now()
    count = 0
    while count < days_ago:
        date -= timedelta(days=1)
        if date.weekday() < 5:
            count += 1
    return date

# Section 1: SARIMAX Forecast
st.sidebar.header("SARIMAX Forecast Settings")
SN = st.sidebar.slider('Seasonality (days)', 7, 30, 22)
Ticker = st.sidebar.text_input('Ticker', 'SPY').upper()
start_date = st.sidebar.date_input('Start Date', value=calculate_business_date(395).date())
end_date = st.sidebar.date_input('End Date', value=calculate_business_date(30).date())

if st.sidebar.button('Run SARIMAX Forecast'):
    with st.spinner('Running SARIMAX model...'):
        # Fetch historical close data
        full_df = yf.Ticker(Ticker).history(start=start_date, end=end_date)
                df = full_df[['Close']].dropna()
        # Ensure index is timezone-aware for New York
        idx = pd.to_datetime(df.index)
        if idx.tz is None:
            idx = idx.tz_localize('America/New_York', nonexistent='shift_forward')
        else:
            idx = idx.tz_convert('America/New_York')
        df.index = idx
