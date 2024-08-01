import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://www.tradingview.com"
    stock_url = f"{base_url}/symbols/NYSE-{ticker}/"
    
    try:
        response = requests.get(stock_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            
            # Extract dividend data from the stock analysis site
            price = tree.xpath('//span[contains(text(), "Price")]/following-sibling::span/text()')[0]
            yield_percent = tree.xpath('//span[contains(text(), "Dividend Yield")]/following-sibling::span/text()')[0]
            annual_dividend = tree.xpath('//span[contains(text(), "Annual Dividend")]/following-sibling::span/text()')[0]
            ex_dividend_date = tree.xpath('//span[contains(text(), "Ex Dividend Date")]/following-sibling::span/text()')[0]
            frequency = tree.xpath('//span[contains(text(), "Frequency")]/following-sibling::span/text()')[0]
            dividend_growth = tree.xpath('//span[contains(text(), "Dividend Growth")]/following-sibling::span/text()')[0]

            # Extract performance data from the TradingView page
            one_day = tree.xpath('//span[contains(text(), "1D")]/../following-sibling::span/text()')[0]
            five_days = tree.xpath('//span[contains(text(), "5D")]/../following-sibling::span/text()')[0]
            one_month = tree.xpath('//span[contains(text(), "1M")]/../following-sibling::span/text()')[0]
            six_months = tree.xpath('//span[contains(text(), "6M")]/../following-sibling::span/text()')[0]
            ytd = tree.xpath('//span[contains(text(), "YTD")]/../following-sibling::span/text()')[0]
            one_year = tree.xpath('//span[contains(text(), "1Y")]/../following-sibling::span/text()')[0]
            five_years = tree.xpath('//span[contains(text(), "5Y")]/../following-sibling::span/text()')[0]
            all_time = tree.xpath('//span[contains(text(), "All")]/../following-sibling::span/text()')[0]

            return {
                "Ticker": ticker, 
                "Price": price, 
                "Yield %": yield_percent, 
                "Annual Dividend": annual_dividend, 
                "Ex Dividend Date": ex_dividend_date, 
                "Frequency": frequency, 
                "Dividend Growth %": dividend_growth,
                "1 Day": one_day,
                "5 Days": five_days,
                "1 Month": one_month,
                "6 Month": six_months,
                "YTD": ytd,
                "1 Year": one_year,
                "5 Year": five_years,
                "All Time": all_time
            }
        else:
            return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", 
                    "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A", 
                    "1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", 
                    "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}
    except:
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", 
                "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A", 
                "1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", 
                "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
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
