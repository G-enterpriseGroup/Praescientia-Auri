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

# Title of the application
st.write("# Stock Forecasting Application - Designed & Implemented by Raj Ghotra")

# Calculate past date from today minus given business days
def calculate_business_days_ago(business_days):
    date = datetime.now()
    while business_days > 0:
        date -= timedelta(days=1)
        if date.weekday() < 5:  # Monday to Friday are considered business days
            business_days -= 1
    return date

# Default dates setup
default_start_date = calculate_business_days_ago(395)
default_end_date = calculate_business_days_ago(30)

# User inputs
SN = st.slider('Seasonality', 7, 30, 22)
Ticker = st.text_input('Ticker', value="SPY")
start_date1 = st.date_input('Start Date', value=default_start_date)
end_date1 = st.date_input('End Date', value=default_end_date)

# Button to execute the SARIMAX model
if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...'):
        # Fetch historical stock data
        df = yf.Ticker(Ticker).history(start=start_date1, end=end_date1)
        df = df[['Close']]
        df.columns = ['Closing Prices']

        # SARIMAX model fitting
        auto_model = auto_arima(df['Closing Prices'], seasonal=True, m=SN)
        model = SARIMAX(df['Closing Prices'], order=auto_model.order, seasonal_order=(0,1,1,SN)).fit()

        # Future dates prediction setup
        future_dates = pd.date_range(df.index.max() + timedelta(days=1), periods=30, freq=CustomBusinessDay(calendar=USFederalHolidayCalendar()))
        predictions = model.predict(start=len(df), end=len(df) + 29)
        future_df = pd.DataFrame({'Forecasted Prices': predictions.values}, index=future_dates)

        # Plot historical and forecasted prices
        plt.figure(figsize=(10, 5))
        plt.plot(df.index, df['Closing Prices'], label='Closing Prices')
        plt.plot(future_df.index, future_df['Forecasted Prices'], label='Forecasted Prices', linestyle='--')
        plt.title(f'{Ticker} Closing Prices and Forecast')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        st.pyplot(plt)

        # Combine and display data
        combined_df = pd.concat([df, future_df], axis=1).ffill().bfill()  # Fill missing values for a continuous comparison
        combined_df['Difference'] = combined_df['Forecasted Prices'] - combined_df['Closing Prices']
        st.write(combined_df)



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
# Check if data is not empty
if not data.empty:
    # Extract dates and closing prices into a new DataFrame
    closing_prices_df = data[['Close']].copy()
    
    # Display the DataFrame in Streamlit
    st.write("Closing Prices DataFrame:", closing_prices_df)
else:
    st.write("No data available for the given ticker.")
#_______________________________________________________________________________________________________________________________________________________________
import streamlit as st
from datetime import datetime
from pandas.tseries.offsets import BDay

def calculate_business_days_ago(target_date, days_ago):
    return target_date - BDay(days_ago)

def get_date_metrics():
    today = datetime.now()
    
    # Calculate 30 business days ago
    business_days_ago_date = calculate_business_days_ago(today, 30).strftime('%Y-%m-%d')
    
    # QTD (Quarterly To Date)
    first_day_of_current_quarter = datetime(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
    qtd_date = first_day_of_current_quarter.strftime('%Y-%m-%d')
    
    # YTD (Year To Date)
    ytd_date = datetime(today.year, 1, 1).strftime('%Y-%m-%d')
    
    # MTD (Month To Date)
    mtd_date = datetime(today.year, today.month, 1).strftime('%Y-%m-%d')
    
    # One Year Ago Date
    one_year_ago_date = (today - BDay(365)).strftime('%Y-%m-%d')
    
    # Two Year Ago Date
    two_year_ago_date = (today - BDay(365 * 2)).strftime('%Y-%m-%d')
    
    # Three Year Ago Date
    three_year_ago_date = (today - BDay(365 * 3)).strftime('%Y-%m-%d')
    
    return business_days_ago_date, qtd_date, ytd_date, mtd_date, one_year_ago_date, two_year_ago_date, three_year_ago_date

def display_dates():
    st.title("Date Calculations")
    
    business_days_ago_date, qtd_date, ytd_date, mtd_date, one_year_ago_date, two_year_ago_date, three_year_ago_date = get_date_metrics()
    
    st.subheader("30 Business Days Ago")
    st.text(business_days_ago_date)
    
    st.subheader("QTD (Quarterly To Date)")
    st.text(qtd_date)
    
    st.subheader("YTD (Year To Date)")
    st.text(ytd_date)
    
    st.subheader("MTD (Month To Date)")
    st.text(mtd_date)
    
    st.subheader("One Year Ago Date")
    st.text(one_year_ago_date)
    
    st.subheader("Two Years Ago Date")
    st.text(two_year_ago_date)
    
    st.subheader("Three Years Ago Date")
    st.text(three_year_ago_date)

# Run the display function
if __name__ == "__main__":
    display_dates()
