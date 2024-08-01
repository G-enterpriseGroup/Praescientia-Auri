import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# Function to get stock performance data using yfinance
def get_performance_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        
        # Fetch historical market data
        hist = stock.history(period="5y")
        
        # Check if historical data is returned correctly
        if hist.empty:
            return {
                "Current Price": "N/A",
                "1 Day": "N/A",
                "1 Month": "N/A",
                "6 Month": "N/A",
                "YTD": "N/A",
                "1 Year": "N/A",
                "5 Year": "N/A",
            }
        
        # Calculate performance metrics
        current_price = hist['Close'][-1]
        one_day_return = ((hist['Close'][-1] / hist['Close'][-2]) - 1) * 100

        # Ensure enough data points exist for each period calculation
        one_month_return = ((hist['Close'][-1] / hist['Close'][-22]) - 1) * 100 if len(hist) >= 22 else "N/A"
        six_month_return = ((hist['Close'][-1] / hist['Close'][-126]) - 1) * 100 if len(hist) >= 126 else "N/A"
        one_year_return = ((hist['Close'][-1] / hist['Close'][-252]) - 1) * 100 if len(hist) >= 252 else "N/A"

        # Calculate YTD return using the closest available trading day at the start of the year
        current_year = datetime.now().year
        start_of_year_index = hist.index.searchsorted(f'{current_year}-01-01')
        
        # Use the closest available date to the start of the year
        if start_of_year_index < len(hist):
            ytd_start_price = hist['Close'][start_of_year_index]
            ytd_return = ((current_price / ytd_start_price) - 1) * 100
        else:
            ytd_return = "N/A"

        five_year_return = ((hist['Close'][-1] / hist['Close'][0]) - 1) * 100 if len(hist) > 0 else "N/A"
        
        performance_data = {
            "Current Price": f"${current_price:.2f}",
            "1 Day": f"{one_day_return:.2f}%" if isinstance(one_day_return, float) else "N/A",
            "1 Month": f"{one_month_return:.2f}%" if isinstance(one_month_return, float) else "N/A",
            "6 Month": f"{six_month_return:.2f}%" if isinstance(six_month_return, float) else "N/A",
            "YTD": f"{ytd_return:.2f}%" if isinstance(ytd_return, float) else "N/A",
            "1 Year": f"{one_year_return:.2f}%" if isinstance(one_year_return, float) else "N/A",
            "5 Year": f"{five_year_return:.2f}%" if isinstance(five_year_return, float) else "N/A",
        }

        return performance_data
    
    except Exception as e:
        st.write(f"Error fetching performance data for {ticker}: {e}")
        return {
            "Current Price": "N/A",
            "1 Day": "N/A",
            "1 Month": "N/A",
            "6 Month": "N/A",
            "YTD": "N/A",
            "1 Year": "N/A",
            "5 Year": "N/A",
        }

# Streamlit App
st.title("Stock Performance Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = []
    for ticker in tickers:
        ticker = ticker.strip().upper()  # Ensure tickers are uppercase
        if ticker:
            performance_data = get_performance_data(ticker)
            combined_data = {"Ticker": ticker, **performance_data}
            data.append(combined_data)
    df = pd.DataFrame(data)
    
    # Display DataFrame
    st.write(df)

# Adjust the width and height of the page and ensure table fits the data
st.markdown(
    """
    <style>
    .reportview-container .main .block-container{
        max-width: 100%;
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
    table {
        width: 100% !important;
        height: 100% !important;
        table-layout: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
