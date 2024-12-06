import streamlit as st
import pandas as pd
import requests
from lxml import html
import yfinance as yf
import time

st.set_page_config(page_title="Stock and ETF Dashboard", layout="wide")

# Function to fetch stock/ETF data
def fetch_stock_data(ticker):
    base_url = f"https://stockanalysis.com/stocks/{ticker}/dividend/"
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            # Adjust these XPaths to match the current website structure
            price = tree.xpath('//div[contains(@class, "price")]/text()')[0].strip()
            yield_percent = tree.xpath('//div[contains(text(), "Yield")]/following-sibling::div/text()')[0].strip()
            annual_dividend = tree.xpath('//div[contains(text(), "Annual Dividend")]/following-sibling::div/text()')[0].strip()
            ex_dividend_date = tree.xpath('//div[contains(text(), "Ex-Dividend Date")]/following-sibling::div/text()')[0].strip()
            frequency = tree.xpath('//div[contains(text(), "Frequency")]/following-sibling::div/text()')[0].strip()
            dividend_growth = tree.xpath('//div[contains(text(), "Dividend Growth")]/following-sibling::div/text()')[0].strip()
            return {
                "Ticker": ticker,
                "Price": price,
                "Yield %": yield_percent,
                "Annual Dividend": annual_dividend,
                "Ex Dividend Date": ex_dividend_date,
                "Frequency": frequency,
                "Dividend Growth %": dividend_growth,
            }
        else:
            return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}
    except Exception as e:
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}

# Streamlit App
st.title("Stock and ETF Dashboard")

# User input for tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

if tickers:
    data = []
    for ticker in tickers:
        ticker = ticker.strip().upper()
        if ticker:
            # Introduce delay to avoid server issues
            time.sleep(8)
            stock_data = fetch_stock_data(ticker)
            stock_data["Name"] = yf.Ticker(ticker).info.get("longName", "N/A")  # Fetch additional info using Yahoo Finance
            data.append(stock_data)
    
    # Create DataFrame
    df = pd.DataFrame(data, columns=["Name", "Ticker", "Price", "Yield %", "Annual Dividend", "Ex Dividend Date", "Frequency", "Dividend Growth %"])
    st.write(df)

    # Display warning if too many requests fail
    failed_tickers = [row["Ticker"] for row in data if row["Price"] == "N/A"]
    if failed_tickers:
        st.warning(f"Data not found for the following tickers: {', '.join(failed_tickers)}. Check ticker validity or server response.")
