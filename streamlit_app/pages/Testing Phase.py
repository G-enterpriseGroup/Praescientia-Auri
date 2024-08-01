import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    base_url2 = "https://www.tradingview.com/symbols"
    url = f"{base_url2}/{ticker}"

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
            return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
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
                return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
            else:
                return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}
    except:
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

# Function to get additional stock data
def get_additional_stock_data(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            data_1d = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[1]/span/span[2]')[0]
            data_5d = tree.xpath('/html/body/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[2]/span/span[2]')[0]
            data_1m = tree.xpath('/html/body/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[3]/span/span[2]')[0]
            data_6m = tree.xpath('/html/body/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[4]/span/span[2]')[0]
            data_ytd = tree.xpath('/html/body/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[5]/span/span[2]')[0]
            data_1y = tree.xpath('/html/body/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[6]/span/span[2]')[0]
            data_5y = tree.xpath('/html/body/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[7]/span/span[2]')[0]
            data_alltime = tree.xpath('/html/body/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[8]/span/span[2]')[0]
            return {"1 Day": data_1d, "5 Days": data_5d, "1 Month": data_1m, "6 Months": data_6m, "YTD": data_ytd, "1 Year": data_1y, "5 Year": data_5y, "All Time": data_alltime}
        else:
            return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Months": "N/A", "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}
    except:
        return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Months": "N/A", "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')



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
