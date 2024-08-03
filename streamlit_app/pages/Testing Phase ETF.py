import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"

    try:
        # Attempt to fetch stock data first
        response = requests.get(stock_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0].strip()
            yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0].strip()
            annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0].strip()
            ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0].strip()
            frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0].strip()
            dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0].strip()
            return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
        else:
            # If stock URL fails, attempt to fetch ETF data
            response = requests.get(etf_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')[0].strip()
                yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')[0].strip()
                annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0].strip()
                ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')[0].strip()
                frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')[0].strip()
                dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')[0].strip()
                return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth}
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")

    return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

# Function to get additional stock data
def get_additional_stock_data(ticker):
    base_url = "https://www.tradingview.com/symbols/" + ticker
    try:
        response = requests.get(base_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                day_1 = tree.xpath('//*[@id="js-category-content"]/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[1]/text()')[0].strip()
                day_5 = tree.xpath('//*[@id="js-category-content"]/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[2]/text()')[0].strip()
                month_1 = tree.xpath('//*[@id="js-category-content"]/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[3]/text()')[0].strip()
                month_6 = tree.xpath('//*[@id="js-category-content"]/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[4]/text()')[0].strip()
                ytd = tree.xpath('//*[@id="js-category-content"]/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[5]/text()')[0].strip()
                year_1 = tree.xpath('//*[@id="js-category-content"]/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[6]/text()')[0].strip()
                year_5 = tree.xpath('//*[@id="js-category-content"]/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[7]/text()')[0].strip()
                all_time = tree.xpath('//*[@id="js-category-content"]/div[4]/div[4]/div/div/div[2]/div/section/div[1]/div[2]/div/div[3]/div/div[2]/button[8]/text()')[0].strip()
                return {"1 Day": day_1, "5 Days": day_5, "1 Month": month_1, "6 Month": month_6, "YTD": ytd, "1 Year": year_1, "5 Year": year_5, "All Time": all_time}
            else:
            return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}
    except Exception as e:
        return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A"}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(data, columns=["Ticker", "Price", "Yield %", "Annual Dividend", "Ex Dividend Date", "Frequency", "Dividend Growth %"])

    # Get additional data for each ticker
    additional_data = [get_additional_stock_data(ticker) for ticker in df["Ticker"]]
    additional_df = pd.DataFrame(additional_data)

    # Combine main data and additional data
    df = pd.concat([df, additional_df], axis=1)

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
