
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
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay


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

def calculate_date(days, start=True):
    current_date = datetime.today()
    delta_days = 0
    while delta_days < days:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:
            delta_days += 1
    return current_date

default_start_date = calculate_date(395)
default_end_date = calculate_date(30, start=False)

split_percentage = st.slider('Training set proportion %', 0.2, 0.99, 0.80)
Ticker = st.text_input('Ticker', value="SPY")
start_date1 = st.date_input('Start Date', value=default_start_date)
end_date1 = st.date_input('End Date', value=default_end_date)

         f'\nTicker: {Ticker}\nStart Date: {start_date1}\nEnd Date: {end_date1}\nTraining set proportion %: {split_percentage}')

if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...Estimated 4 Minutes'):
        progress_bar = st.progress(0)
        df = yf.Ticker(Ticker).history(period="max")
        df = df.loc[pd.to_datetime(start_date1).tz_localize('America/New_York'):pd.to_datetime(end_date1).tz_localize('America/New_York')]
        if df.index.tz is None:
            df.index = pd.to_datetime(df.index).tz_localize('America/New_York')
        else:
            df.index = pd.to_datetime(df.index).tz_convert('America/New_York')
        df = df[['Close']].copy()
        progress_bar.progress(10)

        for ema, value in EMA_values.items():
            df[ema] = df['Close'].ewm(span=value, adjust=False).mean()

        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        C = df["Close"].dropna()
        progress_bar.progress(30)

        auto_model = auto_arima(C, trace=True, suppress_warnings=True)
        arima_order = auto_model.order
        seasonal_order = (arima_order[0], arima_order[1], arima_order[2], SN)
        model = SARIMAX(C, order=arima_order, seasonal_order=seasonal_order).fit()
        progress_bar.progress(80)

        cal = USFederalHolidayCalendar()
        holidays = cal.holidays(start=df.index.max(), end=df.index.max() + pd.DateOffset(days=90))
        future_dates = pd.bdate_range(start=df.index.max(), periods=30 + len(holidays), freq='B')
        future_dates = future_dates[~future_dates.isin(holidays)][:30]

        predictions = model.predict(start=len(C), end=len(C) + len(future_dates) - 1, dynamic=True)
        # Use a built-in holiday calendar
        custom_business_day = CustomBusinessDay(calendar=USFederalHolidayCalendar())
        
        # Generate the date range
        future_dates_index = pd.date_range(start=future_dates[0], periods=len(predictions), freq=custom_business_day)
        predictions.index = future_dates_index

        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['Close'], label='Actual Close')
        plt.plot(predictions.index, predictions, label='Forecast', linestyle='--')
        plt.title(f'{Ticker} Stock Price Forecast')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.tight_layout()

        st.pyplot(plt)
        # Assuming 'predictions' is your forecasted values and 'future_dates_index' are the corresponding future dates
        
        # Create a DataFrame for the forecasted values
        future_df = pd.DataFrame({'Forecasted Price': predictions.values}, index=future_dates_index)
        
        # Display the DataFrame in Streamlit
        st.write(future_df)
        
        # Plotting historical data and future predictions
        plt.figure(figsize=(15, 7))
        plt.plot(future_df.index, future_df['Forecasted Price'], label='Forecasted Price', linestyle='--', color='red')
        plt.title(f'{Ticker} Historical and Forecasted Stock Price')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.tight_layout()
        
        # Show the plot in Streamlit
        st.pyplot(plt)
        
        progress_bar.progress(100)
        st.success("Model run successfully!")

#_______________________________________________________________________________________________________________________________________________________________
# Function to fetch data
def fetch_stock_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    return data

# Streamlit app layout
st.title('30 Days Stock Price Candlestick Chart')

# User input for stock ticker
stock_ticker = st.text_input('Enter Stock Ticker:', Ticker).upper()

# Calculate dates for the last 30 business days
end_date = datetime.today()
start_date = end_date - timedelta(days=43) # Extend the days to ensure we cover 30 business days approximately

# Fetching the stock data
data = fetch_stock_data(stock_ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

# Check if data is empty
if not data.empty:
    # Create the candlestick chart
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'])])

    # Update layout for a better visual
    fig.update_layout(
        title=f'{stock_ticker} Stock Price',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        xaxis_rangeslider_visible=False, # Hide the range slider
        xaxis=dict(
            tickmode='array', # Use an array of custom tick values
            tickvals=data.index[::3], # Show every 3rd label to prevent overlap
            ticktext=[date.strftime('%Y-%m-%d') for date in data.index][::3] # Format date
        )
    )
    
    # Update layout to make it wider
    fig.update_layout(autosize=False, width=800, height=600)

    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No data available for the given ticker.")


import streamlit as st
from datetime import datetime, timedelta
import pyperclip

def calculate_business_days_ago(start_date, business_days):
    while business_days > 0:
        start_date -= timedelta(days=1)
        if start_date.weekday() < 5:  # Monday = 0, Sunday = 6
            business_days -= 1
    return start_date

# Display the app title
st.title('Date 30 Business Days Ago')

# Today's date
today = datetime.now()

# Calculate 30 business days ago
business_days_ago_date = calculate_business_days_ago(today, 30)

# Display the result
date_str = business_days_ago_date.strftime('%Y-%m-%d')

# Display the result for manual copy
st.text_input("Copy the date from here:", date_str, help="Select and copy this date manually.")

# Check if data is not empty
if not data.empty:
    # Extract dates and closing prices into a new DataFrame
    closing_prices_df = data[['Close']].copy()
    
    # Display the DataFrame in Streamlit
    st.write("Closing Prices DataFrame:", closing_prices_df)
else:
    st.write("No data available for the given ticker.")

#_______________________________________________________________________________________________________________________________________________________________
