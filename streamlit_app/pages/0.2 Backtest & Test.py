import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX
import plotly.graph_objects as go
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay, BDay
import warnings

# Attempt to import pmdarima; provide fallback if unavailable
try:
    from pmdarima import auto_arima
    PMDARIMA_AVAILABLE = True
except ImportError:
    PMDARIMA_AVAILABLE = False
    warnings.warn("pmdarima not installed; defaulting to ARIMA(1,1,1)")

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
        # Fetch data
        full_df = yf.Ticker(Ticker).history(start=start_date, end=end_date)
        df = full_df[['Close']].dropna()
        df.index = pd.to_datetime(df.index).tz_localize('America/New_York', nonexistent='shift_forward')

        # Determine ARIMA order
        if PMDARIMA_AVAILABLE:
            auto_model = auto_arima(df['Close'], trace=False, suppress_warnings=True)
            arima_order = auto_model.order
        else:
            arima_order = (1, 1, 1)
            st.info("Using fallback ARIMA order (1,1,1)")

        seasonal_order = (*arima_order, SN)
        # Fit model
        model = SARIMAX(df['Close'], order=arima_order, seasonal_order=seasonal_order).fit(disp=False)

        # Generate future business dates excluding US federal holidays
        cal = USFederalHolidayCalendar()
        holidays = cal.holidays(start=df.index.max(), end=df.index.max()+BDay(60))
        future_idx = pd.bdate_range(start=df.index.max()+BDay(1), periods=30+len(holidays), freq='B')
        future_idx = future_idx.difference(holidays)[:30]

        # Forecast
        forecast = model.get_prediction(start=len(df), end=len(df)+len(future_idx)-1, dynamic=False)
        forecast_vals = forecast.predicted_mean
        forecast_vals.index = future_idx

        # Plot results
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df.index, df['Close'], label='Actual')
        ax.plot(forecast_vals.index, forecast_vals, '--', label='Forecast')
        ax.set_title(f'{Ticker} SARIMAX Forecast')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price (USD)')
        ax.legend()
        st.pyplot(fig)

        # Show forecast table
        st.write(forecast_vals.to_frame('Forecasted Close'))

# Section 2: Candlestick Chart
st.header('30-Day Candlestick Chart')
stock_ticker = st.text_input('Enter Ticker for Candlestick', Ticker).upper()

@st.cache_data
def load_data(ticker, start, end):
    return yf.download(ticker, start=start, end=end)

end_dt = datetime.now()
start_dt = end_dt - timedelta(days=60)
data = load_data(stock_ticker, start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))

if not data.empty:
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close']
    )])
    fig.update_layout(
        title=f'{stock_ticker} Price (Last 30 Business Days)',
        xaxis_title='Date', yaxis_title='Price (USD)',
        xaxis_rangeslider_visible=False,
        autosize=False, width=900, height=500
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning('No data for ticker: ' + stock_ticker)

# Section 3: Date Metrics
st.header('Date Calculations')

today = datetime.now()
metrics = {
    '30 Business Days Ago': (today - BDay(30)).strftime('%Y-%m-%d'),
    'QTD Start': datetime(today.year, 3*((today.month-1)//3)+1, 1).strftime('%Y-%m-%d'),
    'YTD Start': datetime(today.year, 1, 1).strftime('%Y-%m-%d'),
    'MTD Start': datetime(today.year, today.month, 1).strftime('%Y-%m-%d'),
    '1 Year Ago': (today - BDay(365)).strftime('%Y-%m-%d'),
    '2 Years Ago': (today - BDay(365*2)).strftime('%Y-%m-%d'),
    '3 Years Ago': (today - BDay(365*3)).strftime('%Y-%m-%d')
}
for label, date_str in metrics.items():
    st.write(f'**{label}:** {date_str}')
