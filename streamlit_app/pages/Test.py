import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pandas.tseries.offsets import BDay
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Streamlit page configuration
st.set_page_config(layout="wide")
st.title("Stock Forecasting Application - Designed & Implemented by Raj Ghotra")

# Function to calculate business days ago using pandas BDay
def calculate_business_days_ago(business_days):
    return datetime.now() - BDay(business_days)

# Setup default dates for user inputs
default_start_date = calculate_business_days_ago(395)
default_end_date = calculate_business_days_ago(30)
seasonality = st.slider('Seasonality', 7, 30, 22)
ticker = st.text_input('Ticker', value="SPY")
start_date = st.date_input('Start Date', value=default_start_date)
end_date = st.date_input('End Date', value=default_end_date)

# Custom CSS to hide Streamlit branding
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Running SARIMAX model and plotting
if st.button('Run SARIMAX Model'):
    try:
        with st.spinner('Fetching data and running model, please wait...'):
            # Fetch historical stock data
            df = yf.Ticker(ticker).history(start=start_date, end=end_date)
            df = df[['Close']]
            df.columns = ['Closing Prices']

            # SARIMAX model fitting
            model = SARIMAX(df['Closing Prices'], order=(1, 1, 1), seasonal_order=(0, 1, 1, seasonality)).fit(disp=False)
            
            # Predict future prices
            future_dates = pd.date_range(df.index[-1] + pd.Timedelta(days=1), periods=30, freq=BDay())
            predictions = model.predict(start=len(df), end=len(df) + 29, typ='levels')
            future_df = pd.DataFrame({'Forecasted Prices': predictions.values}, index=future_dates)

            # Plotting the results
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df.index, df['Closing Prices'], label='Closing Prices')
            ax.plot(future_df.index, future_df['Forecasted Prices'], label='Forecasted Prices', linestyle='--')
            ax.set_title(f'{ticker} Closing Prices and Forecast')
            ax.set_xlabel('Date')
            ax.set_ylabel('Price')
            ax.legend()
            st.pyplot(fig)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
