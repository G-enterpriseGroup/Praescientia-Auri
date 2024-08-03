import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get data for stock or ETF
def get_data(ticker):
    base_url = "https://stockanalysis.com"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"

    # Attempt to fetch stock data first
    data = fetch_data(stock_url, ticker, is_etf=False)
    
    # If stock data is not found, try fetching ETF data
    if data["Price"] == "N/A":
        data = fetch_data(etf_url, ticker, is_etf=True)

    return data

# Function to fetch and parse data from a given URL
def fetch_data(url, ticker, is_etf=False):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return parse_data(response, is_etf)
        else:
            print(f"Failed to fetch data for {ticker} from {url}")
    except Exception as e:
        print(f"Error fetching data for {ticker} from {url}: {e}")

    return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", 
            "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

# Function to parse data from the response
def parse_data(response, is_etf):
    tree = html.fromstring(response.content)
    
    try:
        price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0].strip()
    except IndexError:
        price = "N/A"
    
    try:
        yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0].strip()
    except IndexError:
        yield_percent = "N/A"
    
    try:
        annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0].strip()
    except IndexError:
        annual_dividend = "N/A"
    
    try:
        ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0].strip()
    except IndexError:
        ex_dividend_date = "N/A"
    
    try:
        frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0].strip()
    except IndexError:
        frequency = "N/A"
    
    try:
        dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0].strip()
    except IndexError:
        dividend_growth = "N/A"

    return {"Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, 
            "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}

# Function to get performance data
def get_performance_data(ticker):
    base_url = "https://www.tradingview.com/symbols/" + ticker
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            return parse_performance_data(tree)
        else:
            print(f"Failed to fetch performance data for {ticker}")
    except Exception as e:
        print(f"Error fetching performance data for {ticker}: {e}")
    
    return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", "YTD": "N/A", 
            "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}

# Function to parse performance data
def parse_performance_data(tree):
    try:
        day_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[1]/span/span[2]/text()')[0].strip()
    except IndexError:
        day_1 = "N/A"
    
    try:
        day_5 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[2]/span/span[2]/text()')[0].strip()
    except IndexError:
        day_5 = "N/A"
    
    try:
        month_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[3]/span/span[2]/text()')[0].strip()
    except IndexError:
        month_1 = "N/A"
    
    try:
        month_6 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[4]/span/span[2]/text()')[0].strip()
    except IndexError:
        month_6 = "N/A"
    
    try:
        ytd = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[5]/span/span[2]/text()')[0].strip()
    except IndexError:
        ytd = "N/A"
    
    try:
        year_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[6]/span/span[2]/text()')[0].strip()
    except IndexError:
        year_1 = "N/A"
    
    try:
        year_5 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[7]/span/span[2]/text()')[0].strip()
    except IndexError:
        year_5 = "N/A"
    
    try:
        all_time = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[8]/span/span[2]/text()')[0].strip()
    except IndexError:
        all_time = "N/A"
    
    return {"1 Day": day_1, "5 Days": day_5, "1 Month": month_1, "6 Month": month_6, "YTD": ytd, 
            "1 Year": year_1, "5 Year": year_5, "All Time": all_time}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = []
    for ticker in tickers:
        ticker = ticker.strip()
        ticker_data = get_data(ticker)
        ticker_data["Ticker"] = ticker
        performance_data = get_performance_data(ticker)
        ticker_data.update(performance_data)
        data.append(ticker_data)
    
    df = pd.DataFrame(data, columns=["Ticker", "Price", "Yield %", "Annual Dividend", "Ex Dividend Date", 
                                     "Frequency", "Dividend Growth %", "1 Day", "5 Days", "1 Month", 
                                     "6 Month", "YTD", "1 Year", "5 Year", "All Time"])
    
    # Display DataFrame
    st.write(df)

# Adjust the width and height of the page and ensure the table fits the data
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
