import pandas as pd
import yfinance as yf
import datetime
import streamlit as st
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima

# Streamlit app setup
st.set_page_config(layout="wide")
def hide_streamlit_branding():
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# Application title
st.write("# Forecasting Stock - Designed & Implemented by Raj Ghotra")

# Sliders and input for model parameters and stock ticker
SN = st.slider('Seasonality', min_value=7, max_value=30, value=22)
Ticker = st.text_input('Ticker', value="AAPL")
default_start_date = datetime.datetime.today() - datetime.timedelta(days=365)
start_date1 = st.date_input('Start Date', value=default_start_date)

# Fetch historical data
@st.cache
def get_data(ticker):
    df = yf.Ticker(ticker).history(period="max")
    return df

# Preprocess data
def preprocess_data(df, start_date):
    df = df.loc[start_date:].copy()
    df = df[['Close']]
    return df

# Auto ARIMA to find best order
def find_best_order(series):
    return auto_arima(series, trace=True, suppress_warnings=True, seasonal=True, m=SN).order

# Fit SARIMAX model
def fit_model(series, order):
    model = SARIMAX(series, order=order, seasonal_order=(1, 1, 1, SN)).fit(disp=0)
    return model

if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...'):
        df = get_data(Ticker)
        df_preprocessed = preprocess_data(df, start_date1)
        
        # Find the best ARIMA order
        order = find_best_order(df_preprocessed['Close'])
        
        # Fit SARIMAX model
        model = fit_model(df_preprocessed['Close'], order)
        
        # Forecast
        forecast_steps = 30  # For example, forecast 30 days ahead
        forecast = model.forecast(steps=forecast_steps)
        
        # Plotting the forecast
        st.line_chart(forecast)
        st.success("Model run successfully!")
