import streamlit as st
import pandas as pd
import requests
from lxml import html
import yfinance as yf

# Function to get dividend data from Stock Analysis
def get_dividend_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    
    try:
        response = requests.get(etf_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0]
            yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0]
            annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
            ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0]
            frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0]
            dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0]
            return {"Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, 
                    "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
        else:
            response = requests.get(stock_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0]
                yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0]
                annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
                ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0]
                frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0]
                dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0]
                return {"Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, 
                        "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
            else:
                return {"Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", 
                        "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}
    except Exception as e:
        st.write(f"Error fetching dividend data for {ticker}: {e}")
        return {"Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", 
                "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

# Function to get stock performance data using yfinance
def get_performance_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        
        # Fetch historical market data
        hist = stock.history(period="5y")
        
        # Check if historical data is returned correctly
        if hist.empty:
            st.write(f"No historical data found for {ticker}. Please check the ticker symbol.")
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
        one_month_return = ((hist['Close'][-1] / hist['Close'][-22]) - 1) * 100 if len(hist) > 22 else "N/A"
        six_month_return = ((hist['Close'][-1] / hist['Close'][-126]) - 1) * 100 if len(hist) > 126 else "N/A"
        one_year_return = ((hist['Close'][-1] / hist['Close'][-252]) - 1) * 100 if len(hist) > 252 else "N/A"
        
        # Calculate YTD return
        ytd_start_index = hist.index.get_loc(f'{hist.index[-1].year}-01-01', method='bfill')
        ytd_return = ((hist['Close'][-1] / hist['Close'][ytd_start_index]) - 1) * 100 if ytd_start_index is not None else "N/A"

        five_year_return = ((hist['Close'][-1] / hist['Close'][0]) - 1) * 100 if len(hist) > 0 else "N/A"
        
        performance_data = {
            "Current Price": current_price,
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
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = []
    for ticker in tickers:
        ticker = ticker.strip()
        if ticker:
            dividend_data = get_dividend_data(ticker)
            performance_data = get_performance_data(ticker)
            combined_data = {"Ticker": ticker, **dividend_data, **performance_data}
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
