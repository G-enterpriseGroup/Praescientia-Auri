import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima
from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import USFederalHolidayCalendar

# Streamlit page configuration
st.set_page_config(layout="wide")
st.title("Stock Forecasting Application - Designed & Implemented by Raj Ghotra")

# Function to calculate business days ago
def calculate_business_days_ago(business_days):
    date = datetime.now()
    while business_days > 0:
        date -= timedelta(days=1)
        if date.weekday() < 5:  # Weekdays are business days
            business_days -= 1
    return date

# Setup default dates for user inputs
default_start_date = calculate_business_days_ago(395)
default_end_date = calculate_business_days_ago(30)
SN = st.slider('Seasonality', 7, 30, 22)
Ticker = st.text_input('Ticker', value="SPY")
start_date = st.date_input('Start Date', value=default_start_date)
end_date = st.date_input('End Date', value=default_end_date)

# Hide Streamlit branding
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Running SARIMAX model and plotting
if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...'):
        # Fetch historical stock data
        df = yf.Ticker(Ticker).history(start=start_date, end=end_date)
        df = df[['Close']]
        df.columns = ['Closing Prices']
        
        # SARIMAX model fitting
        auto_model = auto_arima(df['Closing Prices'], seasonal=True, m=SN)
        model = SARIMAX(df['Closing Prices'], order=auto_model.order, seasonal_order=(0,1,1,SN)).fit()
        
        # Predict future prices
        future_dates = pd.date_range(df.index.max() + timedelta(days=1), periods=30, freq=CustomBusinessDay(calendar=USFederalHolidayCalendar()))
        predictions = model.predict(start=len(df), end=len(df) + 29)
        future_df = pd.DataFrame({'Forecasted Prices': predictions.values}, index=future_dates)
        
        # Combine and calculate differences
        combined_df = pd.concat([df, future_df], axis=1).ffill().bfill()
        combined_df['Difference'] = combined_df['Forecasted Prices'] - combined_df['Closing Prices']
        
        # Plotting the results
        plt.figure(figsize=(10, 5))
        plt.plot(df.index, df['Closing Prices'], label='Closing Prices')
        plt.plot(future_df.index, future_df['Forecasted Prices'], label='Forecasted Prices', linestyle='--')
        plt.title(f'{Ticker} Closing Prices and Forecast')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        st.pyplot(plt)

        # Display combined DataFrame
        st.write(combined_df)
