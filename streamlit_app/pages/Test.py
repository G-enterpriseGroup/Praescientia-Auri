import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

# Streamlit page configuration
st.set_page_config(layout="wide")

# Function to hide Streamlit branding
def hide_streamlit_branding():
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)

hide_streamlit_branding()

# Title and Model Introduction
st.write("# Stock Forecasting - Designed & Implemented by Raj Ghotra")

# Calculate past date from today minus given business days
def calculate_business_days(days, start=True):
    current_date = datetime.today()
    delta_days = 0
    while delta_days < days:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:
            delta_days += 1
    return current_date

# Default date settings
default_start_date = calculate_business_days(395)
default_end_date = calculate_business_days(30, start=False)

# User inputs
SN = st.slider('Seasonality', 7, 30, 22)
Ticker = st.text_input('Ticker', value="SPY")
start_date1 = st.date_input('Start Date', value=default_start_date)
end_date1 = st.date_input('End Date', value=default_end_date)

# Button to run the SARIMAX model
if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...'):
        df = yf.Ticker(Ticker).history(start=start_date1, end=end_date1)['Close']
        model = SARIMAX(df, order=auto_arima(df, seasonal=True, m=SN).order, seasonal_order=(0,1,1,SN)).fit()
        future_dates = pd.date_range(start=df.index.max(), periods=30, freq=CustomBusinessDay(calendar=USFederalHolidayCalendar()))
        predictions = model.predict(start=len(df), end=len(df) + 29)

        # Create a DataFrame for the forecast
        future_df = pd.DataFrame({'Forecasted Price': predictions.values}, index=future_dates)
        
        # Plotting
        plt.figure(figsize=(10, 5))
        plt.plot(df.index, df, label='Actual Close')
        plt.plot(future_df.index, future_df['Forecasted Price'], label='Forecasted Price', linestyle='--')
        plt.title(f'{Ticker} Stock Price and Forecast')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.tight_layout()
        st.pyplot(plt)

        # Display DataFrames side by side and their difference
        combined_df = pd.concat([df, future_df], axis=1)
        combined_df.columns = ['Closing Prices', 'Forecasted Prices']
        combined_df['Difference'] = combined_df['Forecasted Prices'] - combined_df['Closing Prices']
        st.write(combined_df)
