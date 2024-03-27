import pandas as pd
import yfinance as yf
import streamlit as st
from pmdarima import auto_arima
import statsmodels.api as sm
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Initialize Streamlit page
st.set_page_config(layout="wide")
st.title("Forecasting Stock - Designed & Implemented by Raj Ghotra")

# Input widgets
Ticker = st.text_input('Ticker', value="AAPL")
start_date1 = st.date_input('Start Date', value=datetime.today() - timedelta(days=365))
SN = st.slider('Seasonality', min_value=7, max_value=30, value=22)

# Helper function to get and preprocess data
@st.cache
def get_data(Ticker, start_date):
    df = yf.Ticker(Ticker).history(period="max")
    df = df.loc[pd.to_datetime(start_date).tz_localize('America/New_York'):].copy()
    df.index = df.index.tz_localize('America/New_York')
    return df[['Close']]

# Helper function to fit ARIMA model in parallel
def fit_arima(series, seasonal_order):
    stepwise_fit = auto_arima(series, seasonal=True, m=SN, suppress_warnings=True, stepwise=True)
    model = sm.tsa.statespace.SARIMAX(series, order=stepwise_fit.order, seasonal_order=seasonal_order)
    return model.fit()

if st.button('Run Model'):
    with st.spinner('Model is running, please wait...'):
        df = get_data(Ticker, start_date1)

        # Calculate EMAs and MACD
        df['EMA12'] = df['Close'].ewm(span=13, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=39, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']

        # Prepare data for ARIMA modeling
        datasets = {'Close': df['Close'], 'MACD': df['MACD'], 'Signal': df['Signal'], 'Histogram': df['Histogram']}
        seasonal_order = (1, 0, 1, SN)  # Simplified seasonal order for example

        # Parallelize model fitting
        with ThreadPoolExecutor() as executor:
            future_to_series = {executor.submit(fit_arima, series, seasonal_order): name for name, series in datasets.items()}
            for future in future_to_series:
                series_name = future_to_series[future]
                df[f'{series_name}_pred'] = future.result().forecast(steps=30)

        # Display forecasted data (this part can be expanded based on how you want to use/display the predictions)
    st.write(df[['Close_pred', 'MACD_pred', 'Signal_pred']])
