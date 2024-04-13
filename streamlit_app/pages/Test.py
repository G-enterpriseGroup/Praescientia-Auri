import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima

st.set_page_config(layout="wide")

def hide_streamlit_branding():
    """Hides Streamlit's default branding."""
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

hide_streamlit_branding()
st.title("Forecasting Stock - Designed & Implemented by Raj Ghotra")

def calculate_date(days, start=True):
    """Calculates dates excluding weekends."""
    date = datetime.today()
    while days > 0:
        date -= timedelta(days=1)
        if date.weekday() < 5:  # Mon-Fri are considered
            days -= 1
    return date

# Constants
default_start_date = calculate_date(395)
default_end_date = calculate_date(30, start=False)

# User inputs
SN = st.slider('Seasonality', 7, 30, 22)
Ticker = st.text_input('Ticker', value="SPY")
start_date1 = st.date_input('Start Date', value=default_start_date)
end_date1 = st.date_input('End Date', value=default_end_date)

st.write(f'Days Predicting: 30\nSeasonality: {SN}\nTicker: {Ticker}\nStart Date: {start_date1}\nEnd Date: {end_date1}')

if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...Estimated 4 Minutes'):
        progress_bar = st.progress(0)
        df = yf.Ticker(Ticker).history(start=start_date1, end=end_date1)
        C = df["Close"].dropna()
        progress_bar.progress(30)
        
        auto_model = auto_arima(C, trace=True, suppress_warnings=True)
        arima_order = auto_model.order
        seasonal_order = (arima_order[0], arima_order[1], arima_order[2], SN)
        
        model = SARIMAX(C, order=arima_order, seasonal_order=seasonal_order).fit()
        progress_bar.progress(80)
        
        future_dates = pd.bdate_range(start=C.index[-1], periods=30, freq=CustomBusinessDay(calendar=USFederalHolidayCalendar()))
        predictions = model.predict(start=len(C), end=len(C) + 29, dynamic=True)
        predictions.index = future_dates
        
        plt.figure(figsize=(10, 6))
        plt.plot(C.index, C, label='Actual Close')
        plt.plot(future_dates, predictions, label='Forecast', linestyle='--')
        plt.title(f'{Ticker} Stock Price Forecast')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.tight_layout()
        st.pyplot(plt)
        
        future_df = pd.DataFrame({'Forecasted Price': predictions}, index=future_dates)
        st.write(future_df)
        
        progress_bar.progress(100)
        st.success("Model run successfully!")
