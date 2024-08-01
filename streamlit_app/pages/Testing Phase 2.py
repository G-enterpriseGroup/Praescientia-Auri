import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data from StockAnalysis
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"

    # Define a function to extract the data
    def extract_data(tree):
        try:
            price = tree.xpath('//*[@data-test="quote-price"]/text()')[0].strip()
            yield_percent = tree.xpath('//*[contains(text(), "Dividend Yield")]/following-sibling::div/text()')[0].strip()
            annual_dividend = tree.xpath('//*[contains(text(), "Annual Dividend")]/following-sibling::div/text()')[0].strip()
            ex_dividend_date = tree.xpath('//*[contains(text(), "Ex-Dividend Date")]/following-sibling::div/text()')[0].strip()
            frequency = tree.xpath('//*[contains(text(), "Dividend Frequency")]/following-sibling::div/text()')[0].strip()
            dividend_growth = tree.xpath('//*[contains(text(), "Dividend Growth")]/following-sibling::div/text()')[0].strip()
            return {
                "Ticker": ticker,
                "Price": price,
                "Yield %": yield_percent,
                "Annual Dividend": annual_dividend,
                "Ex Dividend Date": ex_dividend_date,
                "Frequency": frequency,
                "Dividend Growth %": dividend_growth
            }
        except IndexError:
            # In case any data is not found, return N/A
            return {
                "Ticker": ticker,
                "Price": "N/A",
                "Yield %": "N/A",
                "Annual Dividend": "N/A",
                "Ex Dividend Date": "N/A",
                "Frequency": "N/A",
                "Dividend Growth %": "N/A"
            }

    try:
        # Try fetching from ETF URL first
        response = requests.get(etf_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            return extract_data(tree)
        else:
            # If ETF URL fails, try stock URL
            response = requests.get(stock_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                return extract_data(tree)
            else:
                return {
                    "Ticker": ticker,
                    "Price": "N/A",
                    "Yield %": "N/A",
                    "Annual Dividend": "N/A",
                    "Ex Dividend Date": "N/A",
                    "Frequency": "N/A",
                    "Dividend Growth %": "N/A"
                }
    except Exception as e:
        return {
            "Ticker": ticker,
            "Price": "N/A",
            "Yield %": "N/A",
            "Annual Dividend": "N/A",
            "Ex Dividend Date": "N/A",
            "Frequency": "N/A",
            "Dividend Growth %": "N/A"
        }

# Function to get additional stock data from TradingView
def get_additional_stock_data(ticker):
    base_url = f"https://www.tradingview.com/symbols/{ticker}/"
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            # Use a general method for finding text next to labels
            performance = {}
            labels = tree.xpath('//span[contains(text(), "day") or contains(text(), "month") or contains(text(), "year") or contains(text(), "time") or contains(text(), "5 days")]/text()')
            values = tree.xpath('//span[contains(@class, "change")]/text()')
            for label, value in zip(labels, values):
                performance[label] = value.strip()
            return performance
        else:
            return {
                "1 Day": "N/A",
                "5 Days": "N/A",
                "1 Month": "N/A",
                "6 Months": "N/A",
                "1 Year": "N/A",
                "5 Years": "N/A",
                "All Time": "N/A"
            }
    except Exception as e:
        return {
            "1 Day": "N/A",
            "5 Days": "N/A",
            "1 Month": "N/A",
            "6 Months": "N/A",
            "1 Year": "N/A",
            "5 Years": "N/A",
            "All Time": "N/A"
        }

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
    additional_df = pd.DataFrame(additional_data, columns=["1 Day", "5 Days", "1 Month", "6 Months", "1 Year", "5 Years", "All Time"])

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
