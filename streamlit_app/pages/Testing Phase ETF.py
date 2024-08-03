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
        else:
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
                return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}
    except Exception as e:
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A"}


# Function to get additional stock data
def get_additional_stock_data(ticker):
    base_url = "https://www.tradingview.com/symbols/" + ticker
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            day_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[1]/span/span[2]/text()')[0].strip()
            day_5 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[2]/span/span[2]/text()')[0].strip()
            month_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[3]/span/span[2]/text()')[0].strip()
            month_6 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[4]/span/span[2]/text()')[0].strip()
            ytd = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[5]/span/span[2]/text()')[0].strip()
            year_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[6]/span/span[2]/text()')[0].strip()
            year_5 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[7]/span/span[2]/text()')[0].strip()
            all_time = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[8]/span/span[2]/text()')[0].strip()
            return {"1 Day": day_1, "5 Days": day_5, "1 Month": month_1, "6 Month": month_6, "YTD": ytd, "1 Year": year_1, "5 Year": year_5, "All Time": all_time}
        else:
            return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}
    except Exception as e:
        return {"1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A", "6 Month": "N/A", "YTD": "N/A", "1 Year": "N/A", "5 Year": "N/A", "All Time": "N/A"}


# Function to get ETF performance data
def get_etf_performance_data(ticker):
    base_url = "https://www.tradingview.com/symbols/" + ticker
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            # Modify the XPaths below with the correct ones for ETF performance data
            etf_day_1 = tree.xpath('CORRECT_XPATH_FOR_ETF_1_DAY')[0].strip()
            etf_day_5 = tree.xpath('CORRECT_XPATH_FOR_ETF_5_DAY')[0].strip()
            etf_month_1 = tree.xpath('CORRECT_XPATH_FOR_ETF_1_MONTH')[0].strip()
            etf_month_6 = tree.xpath('CORRECT_XPATH_FOR_ETF_6_MONTH')[0].strip()
            etf_ytd = tree.xpath('CORRECT_XPATH_FOR_ETF_YTD')[0].strip()
            etf_year_1 = tree.xpath('CORRECT_XPATH_FOR_ETF_1_YEAR')[0].strip()
            etf_year_5 = tree.xpath('CORRECT_XPATH_FOR_ETF_5_YEAR')[0].strip()
            etf_all_time = tree.xpath('CORRECT_XPATH_FOR_ETF_ALL_TIME')[0].strip()
            return {"ETF 1 Day": etf_day_1, "ETF 5 Days": etf_day_5, "ETF 1 Month": etf_month_1, "ETF 6 Month": etf_month_6, "ETF YTD": etf_ytd, "ETF 1 Year": etf_year_1, "ETF 5 Year": etf_year_5, "ETF All Time": etf_all_time}
        else:
            return {"ETF 1 Day": "N/A", "ETF 5 Days": "N/A", "ETF 1 Month": "N/A", "ETF 6 Month": "N/A", "ETF YTD": "N/A", "ETF 1 Year": "N/A", "ETF 5 Year": "N/A", "ETF All Time": "N/A"}
    except Exception as e:
        return {"ETF 1 Day": "N/A", "ETF 5 Days": "N/A", "ETF 1 Month": "N/A", "ETF 6 Month": "N/A", "ETF YTD": "N/A", "ETF 1 Year": "N/A", "ETF 5 Year": "N/A", "ETF All Time": "N/A"}


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

    # Get ETF performance data for each ticker
    etf_performance_data = [get_etf_performance_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    etf_performance_df = pd.DataFrame(etf_performance_data)

    # Combine all dataframes
    df = pd.concat([df, etf_performance_df], axis=1)

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
