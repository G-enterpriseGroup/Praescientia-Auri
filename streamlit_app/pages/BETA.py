import pandas as pd
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta
from statsmodels.tsa.arima.model import ARIMA
from pmdarima import auto_arima
import statsmodels.api as sm
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure

# Improved and streamlined layout setup
st.set_page_config(layout="wide")
st.title("Forecasting Stock - Designed & Implemented by Raj Ghotra")

# Simplified function to hide Streamlit branding and sidebar
def hide_streamlit_branding():
    st.markdown("""
        <style>
            #MainMenu, header, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# Function to calculate start or end date excluding weekends
def calculate_date(days, start=True):
    current_date = datetime.today()
    delta_days = 0
    while delta_days < days:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:  # Monday to Friday
            delta_days += 1
    return current_date

# Define UI elements for user input
SN, EMA12, EMA26, EMA9 = [st.slider(label, 0, 100, default) for label, default in [
    ('Seasonality', 22), ('EMA12', 13), ('EMA26', 39), ('EMA9', 9)
]]
split_percentage = st.slider('Training set proportion %', 0.2, 0.99, 0.80)
Ticker = st.text_input('Ticker', value="SPY")
default_start_date = calculate_date(395)
default_end_date = calculate_date(30)
start_date1 = st.date_input('Start Date', value=default_start_date)
end_date1 = st.date_input('End Date', value=default_end_date)

# Display the current values of the variables
for var_name, var_value in [
    ('Days Predicting', 30), ('Seasonality', SN), ('EMA12', EMA12), ('EMA26', EMA26),
    ('EMA9', EMA9), ('Ticker', Ticker), ('Start Date', start_date1), ('End Date', end_date1),
    ('Training set proportion %', split_percentage)
]:
    st.write(f"{var_name}: {var_value}")

if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...Estimated 4 Minutes'), st.empty():
        progress_bar = st.progress(0)

        df = yf.Ticker(Ticker).history(period="max")
        df = df[start_date1:end_date1]  # Filter by the date range
        df = df[['Close']]  # Keep only the 'Close' column

        # Calculate EMA and MACD
        for span in [EMA12, EMA26, EMA9]:
            df[f'EMA_{span}'] = df['Close'].ewm(span=span, adjust=False).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df.drop(columns=['EMA_12', 'EMA_26', 'EMA_9'], inplace=True)

        progress_bar.progress(20)

        # Simplified ARIMA and SARIMAX model fitting
        C = df["Close"].dropna()
        split_index = int(len(C) * split_percentage)
        C_train, C_test = C[:split_index], C[split_index:]
        
        # Display data split information
        st.write(f"Training Data: {len(C_train)} records")
        st.write(f"Testing Data: {len(C_test)} records")

        model_fit = auto_arima(C_train, trace=True, suppress_warnings=True)
        arima_order = model_fit.order

        progress_bar.progress(50)

        model = sm.tsa.statespace.SARIMAX(C, order=arima_order, seasonal_order=(SN, 1, 0, 12))
        results = model.fit()
        Cpred = results.predict(start=split_index, end=len(C)-1)
        Cpred_future = results.predict(start=len(C), end=len(C)+29)

        progress_bar.progress(80)

        # Plotting
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df.index, df['Close'], label='Actual Close')
        ax.plot(Cpred.index, Cpred, label='Predicted Close')
        ax.plot(Cpred_future.index, Cpred_future, label='Future Close', linestyle='--')
        ax.set_title(f'{Ticker} Stock Close Price Forecast')
        ax.legend()
        ax.grid(True)
        
        st.pyplot(fig)
        progress_bar.progress(100)
        st.success("Model run successfully!")

