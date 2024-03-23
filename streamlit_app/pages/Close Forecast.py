import plotly.graph_objects as go
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
import yfinance as yf
import datetime
from datetime import datetime, timedelta
import os, pickle
import streamlit as st


st.set_page_config(layout="wide")

# Function to hide Streamlit branding and sidebar
def hide_streamlit_branding():
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# Set the title of the app
st.write("""
# Forecasting Stock - Designed & Implemented by Raj Ghotra
""")

# Create sliders for each variable
DD = 30
SN = st.slider('Seasonality', min_value=7, max_value=30, value=22)
EMA12 = st.slider('EMA12', min_value=0, max_value=100, value=13)
EMA26 = st.slider('EMA26', min_value=0, max_value=100, value=39)
EMA9 = st.slider('EMA9', min_value=0, max_value=100, value=9)

# Text input for Ticker
Ticker = st.text_input('Ticker', value="AAPL")

from datetime import datetime, timedelta
import streamlit as st
import yfinance as yf
import pandas as pd



# Function to calculate the start date excluding weekends
def calculate_start_date(days):
    start_date = datetime.today()
    delta_days = 0
    while delta_days < days:
        start_date -= timedelta(days=1)
        if start_date.weekday() < 5:  # 0-4 are Monday to Friday
            delta_days += 1
    return start_date

# Function to calculate the end date excluding weekends
def calculate_end_date(days):
    end_date = datetime.today()
    delta_days = 0
    while delta_days < days:
        end_date -= timedelta(days=1)
        if end_date.weekday() < 5:  # 0-4 are Monday to Friday
            delta_days += 1
    return end_date

# Modified code
default_start_date = calculate_start_date(395)
default_end_date = calculate_end_date(30)



# Input for start date
start_date1 = st.date_input('Start Date', value=default_start_date)
# Input for end date
end_date1 = st.date_input('End Date', value=default_end_date)

# Display the current values of the variables
st.write('Days Predicting:', DD)
st.write('Seasonality:', SN)
st.write('EMA12:', EMA12)
st.write('EMA26:', EMA26)
st.write('EMA9:', EMA9)
st.write('Ticker:', Ticker)
st.write('Start Date:', start_date1)
st.write('End Date:', end_date1)

if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...Estimated 4 Minutes'):
        progress_bar = st.progress(0)

        # Retrieve data for the specified ticker
        df = yf.Ticker(Ticker)
        df = df.history(period="max")

        # Convert start and end dates to datetime and localize to New York time
        start_date1 = pd.to_datetime(start_date1).tz_localize('America/New_York')
        end_date1 = pd.to_datetime(end_date1).tz_localize('America/New_York')

        # Filter the DataFrame for the date range
        df = df.loc[start_date1:end_date1].copy()
        df.index = df.index.strftime('%Y-%m-%d')
        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize('America/New_York')


        del df['Open']
        del df['High']
        del df['Low']
        del df['Volume']
        del df['Dividends']
        del df['Stock Splits']
        progress_bar.progress(1)


        # Calculating the 12 EMA
        df['EMA_19'] = df['Close'].ewm(span=EMA12, adjust=False).mean()
        df['EMA_39'] = df['Close'].ewm(span=EMA26, adjust=False).mean()
        df['EMA_9'] = df['Close'].ewm(span=EMA9, adjust=False).mean()
        df['MACD'] = df['EMA_19'] - df['EMA_39']
        # Assuming df['MACD'] is already calculated as shown in your code
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        del df['EMA_19']
        del df['EMA_39']
        del df['EMA_9']
        progress_bar.progress(2)


        C = df["Close"].dropna().tolist()
        M = df["MACD"].dropna().tolist()
        S = df["Signal"].dropna().tolist()
        from statsmodels.tsa.arima.model import ARIMA
        from pmdarima import auto_arima
        progress_bar.progress(4)

        split_percentage = 0.80  # % for training
        split_index = int(len(C) * split_percentage)
        progress_bar.progress(8)

        C_train = M[:split_index]
        C_test = M[split_index:]
        print(len(C_train), len(C_test))
        progress_bar.progress(9)


        stepwise_fit = auto_arima(C,trace=True,suppress_warnings=True)
        stepwise_fit
        progress_bar.progress(16)
        
        def extract_best_arima_order(stepwise_fit):
            # Search for the line starting with "Best model:"
            for line in stepwise_fit.split('\n'):
                if line.startswith("Best model:"):
                    # Extract numbers within parentheses
                    order = tuple(map(int, line.split('ARIMA')[1].split('(')[1].split(')')[0].split(',')))
                    return order
            return None
        arima_order = stepwise_fit.order
        arima_order
        cp, cd, cq = arima_order

        progress_bar.progress(25)

        import statsmodels.api as sm


        arima_order = arima_order
        seasonal_order = (cp, cd, cq, SN)  
        progress_bar.progress(26)

        model = sm.tsa.statespace.SARIMAX(C, order=arima_order, seasonal_order=seasonal_order)
        model = model.fit()
        progress_bar.progress(27)

        start=len(C_train)
        end=len(C_train)+len(C_test)-1
        Cpred = model.predict(start=start,end=end)
        progress_bar.progress(28)

        Cpred_future = model.predict(start=end,end=end+DD)
        progress_bar.progress(29)



        # Assuming df.index is already set to datetime
        last_date = df.index[-2]  # Get the second to last date from the index
        start_date = last_date + pd.tseries.offsets.BDay(1)  # Calculate the start date as one business day after the last date
        progress_bar.progress(38)

        dates = [start_date + pd.Timedelta(days=idx) for idx in range(43)]  # Generate a list of dates starting from 'start_date'
        progress_bar.progress(39)


        # Filter out the weekend dates from the list
        market_dates = [date for date in dates if date.weekday() < 5]
        progress_bar.progress(40)

        Date = pd.Series(market_dates )
        Date
        progress_bar.progress(41)

        df3 = pd.DataFrame({'Date':Date,'Cpred_future': Cpred_future})
        df3
        progress_bar.progress(42)

        import matplotlib.pyplot as plt
        import pandas as pd
        today = datetime.now().strftime("%Y-%m-%d")
        # Assuming df3 and df are already defined and Ticker is defined
        progress_bar.progress(45)

        # Convert 'Date' to datetime if it's not already
        df3['Date'] = pd.to_datetime(df3['Date'])
        progress_bar.progress(46)

        # Set the 'Date' column as the index of the DataFrame
        df3.set_index('Date', inplace=True)
        progress_bar.progress(47)

        # Create a figure and a set of subplots
        fig, ax = plt.subplots(figsize=(20, 12))
        
        # Plotting Close Future predictions
        ax.plot(df3.index, df3['Cpred_future'], label='Close Future', marker='o', color='blue')
        ax.set_title(f'Forecast Closing of {Ticker} from Start Date: {start_date1}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Values')
        ax.legend()
        ax.grid(True)
        ax.tick_params(axis='x', rotation=45)
        ax.set_xticks(df3.index) 

        plt.tight_layout()  # Adjusts the subplot params so that subplots are nicely fit in the figure
        # Assume 'fig' is your matplotlib figure object
        fig_path = "figure.png"  # Specify the path and file name to save the figure
        fig.savefig(fig_path)  # Save the figure to a file
        st.pyplot(fig)  # Display the figure in Streamlit
        today_date = datetime.now().strftime("%Y-%m-%d")
        # Read the file into a buffer
        with open(fig_path, "rb") as file:
            btn = st.download_button(
                    label="Download Figure",
                    data=file,
                    file_name=f"{Ticker}-{today_date}-Zoomed.png",
                    mime="image/png"
                )        
        progress_bar.progress(49)

        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import pandas as pd
        import numpy as np
        today = datetime.now().strftime("%Y-%m-%d")

        # Assuming 'df' and 'df3' are your DataFrames, and their indexes are of datetime type.
        # Also assuming 'df' already has 'MACD', 'Signal', 'Close' columns calculated.
        # 'df3' should contain your future predictions 'Mpred_future', 'Spred_future', 'Cpred_future', 'Hpred_future'.

        # Sorting the DataFrame by the index (date) to ensure the data is in chronological order
        df = df.sort_index()
        progress_bar.progress(51)
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        fig, axs = plt.subplots(1, 2, figsize=(14.875, 19.25), dpi=300)
        fig.suptitle(f"{Ticker}-Data Used for Forecasting {start_date1} to {today} for {DD} Days Forecast", fontsize=25, y=.99)
        
        # Plot Close price
        axs[0].plot(df.index, df['Close'], label='Close', color='Black')
        axs[0].set_title('Close Price')
        axs[0].legend(loc='upper left')
        axs[0].grid(True)
        axs[0].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=45))
        axs[0].xaxis.set_major_formatter(mdates.ConciseDateFormatter(axs[0].xaxis.get_major_locator()))
        
        # Plot Forecast Closing Price
        axs[1].plot(df.index, df['Close'], label='Closed', color='Black')
        axs[1].plot(df3.index[-1000:], df3['Cpred_future'][-1000:], label='Closing Future', linestyle='--', color='Blue')
        axs[1].set_title('Forecast Closing Price')
        axs[1].legend(loc='upper left')
        axs[1].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=45))
        axs[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(axs[1].xaxis.get_major_locator()))

        
        # General settings for all subplots
        for ax in axs:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            ax.grid(True)
            ax.set_xlabel('Date')
            ax.set_ylabel('Value')
        plt.tight_layout(pad=1)
        fig_path = "figure.png"  # Specify the path and file name to save the figure
        fig.savefig(fig_path)  # Save the figure to a file
        st.pyplot(fig)  # Display the figure in Streamlit
        today_date = datetime.now().strftime("%Y-%m-%d")
        # Read the file into a buffer
        with open(fig_path, "rb") as file:
            btn = st.download_button(
                    label="Download Figure",
                    data=file,
                    file_name=f"{Ticker}-{today_date}-Consolidated.png",
                    mime="image/png",
                    key=f"download_{today_date}_{Ticker}"  # Unique key using today's date and Ticker
                )  
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
stock_ticker = st.text_input('Enter Stock Ticker:', 'AAPL').upper()

# Calculate dates for the last 30 business days
end_date = datetime.today()
start_date = end_date - timedelta(days=45) # Extend the days to ensure we cover 30 business days approximately

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
#_______________________________________________________________________________________________________________________________________________________________
