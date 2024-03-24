import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import streamlit as st
from statsmodels.tsa.arima.model import ARIMA
import statsmodels.api as sm
from pmdarima import auto_arima

# Set Streamlit page config
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

# Streamlit app title
st.write("# Forecasting Stock - Designed & Implemented by Raj Ghotra")

# Sliders for model parameters
DD = 30
SN = st.slider('Seasonality', min_value=7, max_value=30, value=22)
EMA12 = st.slider('EMA12', min_value=0, max_value=100, value=13)
EMA26 = st.slider('EMA26', min_value=0, max_value=100, value=39)
EMA9 = st.slider('EMA9', min_value=0, max_value=100, value=9)
split_percentage = st.slider('Training set proportion %', min_value=0.2, max_value=0.99, value=0.80)
Ticker = st.text_input('Ticker', value="SPY")

# Calculate start and end dates excluding weekends
def calculate_start_date(days):
    start_date = datetime.today()
    delta_days = 0
    while delta_days < days:
        start_date -= timedelta(days=1)
        if start_date.weekday() < 5:  # Monday to Friday
            delta_days += 1
    return start_date

default_start_date = calculate_start_date(395)
default_end_date = calculate_start_date(30)

start_date1 = st.date_input('Start Date', value=default_start_date)
end_date1 = st.date_input('End Date', value=default_end_date)

# Display variable values
st.write(f"""Days Predicting: {DD}, Seasonality: {SN}, EMA12: {EMA12}, EMA26: {EMA26}, 
EMA9: {EMA9}, Ticker: {Ticker}, Start Date: {start_date1}, End Date: {end_date1}, 
Training set proportion %: {split_percentage}""")

if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...Estimated 4 Minutes'):
        progress_bar = st.progress(0)
        
        df = yf.Ticker(Ticker).history(period="max")
        df = df.loc[pd.to_datetime(start_date1).tz_localize('America/New_York'):pd.to_datetime(end_date1).tz_localize('America/New_York')]

        # Data preparation
        df.drop(columns=['Open', 'High', 'Low', 'Volume', 'Dividends', 'Stock Splits'], inplace=True)
        df['EMA_12'] = df['Close'].ewm(span=EMA12, adjust=False).mean()
        df['EMA_26'] = df['Close'].ewm(span=EMA26, adjust=False).mean()
        df['EMA_9'] = df['Close'].ewm(span=EMA9, adjust=False).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df.drop(columns=['EMA_12', 'EMA_26', 'EMA_9'], inplace=True)

        progress_bar.progress(10)

        # SARIMAX Model
        stepwise_fit = auto_arima(df['Close'], trace=True, suppress_warnings=True)
        model = sm.tsa.statespace.SARIMAX(df['Close'], order=stepwise_fit.order, seasonal_order=(stepwise_fit.order[0], stepwise_fit.order[1], stepwise_fit.order[2], SN)).fit()

        progress_bar.progress(20)

        # Forecast
        Cpred_future = model.predict(start=len(df), end=len(df)+DD)
        progress_bar.progress(30)

        # Plotting
        fig, axs = plt.subplots(2, 1, figsize=(15, 10))
        axs[0].plot(df.index, df['Close'], label='Close Price', color='blue')
        axs[1].plot(Cpred_future.index, Cpred_future, label='Forecasted Close Price', color='red')
        for ax in axs:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            ax.grid(True)
            ax.legend()

        axs[0].set_title('Historical Close Prices')
        axs[1].set_title('Forecasted Close Prices')

        fig.tight_layout()
        st.pyplot(fig)

        progress_bar.progress(100)
        st.success("Model run successfully!")

# Function to fetch and display stock data using a candlestick chart
def display_candlestick_chart(ticker):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=45)  # Adjust to ensure covering 30 business days

    data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

    if not data.empty:
        fig = go.Figure(data=[go.Candlestick(x=data.index,
                                             open=data['Open'],
                                             high=data['High'],
                                             low=data['Low'],
                                             close=data['Close'])])

        fig.update_layout(title=f'{ticker} Stock Price', xaxis_title='Date', yaxis_title='Price (USD)',
                          xaxis_rangeslider_visible=False, xaxis=dict(tickmode='array',
                          tickvals=data.index[::3], ticktext=[date.strftime('%Y-%m-%d') for date in data.index][::3]))

        fig.update_layout(autosize=False, width=800, height=600)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No data available for the given ticker.")

# Display candlestick chart for the entered stock ticker
display_candlestick_chart(Ticker.upper())
