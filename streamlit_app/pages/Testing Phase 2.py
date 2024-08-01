import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    tradingview_url = f"https://www.tradingview.com/symbols/NYSE-{ticker}/"
    
    # Define a function to extract stock data
    def extract_stock_data(tree):
        price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0]
        yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0]
        annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
        ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0]
        frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0]
        dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0]
        return {"Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, 
                "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
    
    try:
        # Try to get data from stockanalysis
        response = requests.get(etf_url)
        if response.status_code != 200:
            response = requests.get(stock_url)
        
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            stock_data = extract_stock_data(tree)
        else:
            stock_data = {"Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", 
                          "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

        # Try to get performance data from TradingView
        response = requests.get(tradingview_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            one_day = tree.xpath('//span[contains(text(), "1D")]/../following-sibling::span/text()')[0]
            five_days = tree.xpath('//span[contains(text(), "5D")]/../following-sibling::span/text()')[0]
            one_month = tree.xpath('//span[contains(text(), "1M")]/../following-sibling::span/text()')[0]
            six_months = tree.xpath('//span[contains(text(), "6M")]/../following-sibling::span/text()')[0]
            ytd = tree.xpath('//span[contains(text(), "YTD")]/../following-sibling::span/text()')[0]
            one_year = tree.xpath('//span[contains(text(), "1Y")]/../following-sibling::span/text()')[0]
            five_years = tree.xpath('//span[contains(text(), "5Y")]/../following-sibling::span/text()')[0]
            all_time = tree.xpath('//span[contains(text(), "All")]/../following-sibling::span/text()')[0]

            stock_data.update({
                "1 Day": one_day,
                "5 Days": five_days,
                "1 Month": one_month,
                "6 Month": six_months,
                "YTD": ytd,
                "1 Year": one_year,
                "5 Year": five_years,
                "All Time": all_time
            })
        else:
            stock_data.update({
                "1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A",
                "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"
            })

        return {"Ticker": ticker, **stock_data}

    except Exception as e:
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
