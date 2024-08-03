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
            return {
                "Ticker": ticker, "Price": price, "Yield %": yield_percent,
                "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date,
                "Frequency": frequency, "Dividend Growth %": dividend_growth
            }
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
                return {
                    "Ticker": ticker, "Price": price, "Yield %": yield_percent,
                    "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date,
                    "Frequency": frequency, "Dividend Growth %": dividend_growth
                }
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")

    return {
        "Ticker": ticker, "Price": "N/A", "Yield %": "N/A",
        "Annual Dividend": "N/A", "Ex Dividend Date": "N/A",
        "Frequency": "N/A", "Dividend Growth %": "N/A"
    }

# Function to get additional ETF data
def get_additional_etf_data(ticker):
    base_url = "https://www.tradingview.com/symbols/" + ticker + "/"
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)

            # Attempt to fetch performance data using updated XPath
            try:
                day_1 = tree.xpath('//button[@class="rangeButtonRed-tEo1hPMj rangeButton-tEo1hPMj selected-tEo1hPMj"]/span[@class="change-tEo1hPMj"]/text()')[0].strip()
            except IndexError:
                day_1 = "N/A"

            try:
                day_5 = tree.xpath('//button[@class="rangeButtonRed-tEo1hPMj rangeButton-tEo1hPMj"][span/span[text()="5 days"]]/span[@class="change-tEo1hPMj"]/text()')[0].strip()
            except IndexError:
                day_5 = "N/A"

            try:
                month_1 = tree.xpath('//button[@class="rangeButtonRed-tEo1hPMj rangeButton-tEo1hPMj"][span/span[text()="1 month"]]/span[@class="change-tEo1hPMj"]/text()')[0].strip()
            except IndexError:
                month_1 = "N/A"

            try:
                month_6 = tree.xpath('//button[@class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"][span/span[text()="6 months"]]/span[@class="change-tEo1hPMj"]/text()')[0].strip()
            except IndexError:
                month_6 = "N/A"

            try:
                ytd = tree.xpath('//button[@class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"][span/span[text()="Year to date"]]/span[@class="change-tEo1hPMj"]/text()')[0].strip()
            except IndexError:
                ytd = "N/A"

            try:
                year_1 = tree.xpath('//button[@class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"][span/span[text()="1 year"]]/span[@class="change-tEo1hPMj"]/text()')[0].strip()
            except IndexError:
                year_1 = "N/A"

            try:
                year_5 = tree.xpath('//button[@class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"][span/span[text()="5 years"]]/span[@class="change-tEo1hPMj"]/text()')[0].strip()
            except IndexError:
                year_5 = "N/A"

            try:
                all_time = tree.xpath('//button[@class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"][span/span[text()="All time"]]/span[@class="change-tEo1hPMj"]/text()')[0].strip()
            except IndexError:
                all_time = "N/A"

            return {
                "1 Day": day_1, "5 Days": day_5, "1 Month": month_1,
                "6 Month": month_6, "YTD": ytd, "1 Year": year_1,
                "5 Year": year_5, "All Time": all_time
            }
        else:
            print(f"Failed to fetch data for {ticker}, status code: {response.status_code}")
            return {
                "1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A",
                "6 Month": "N/A", "YTD": "N/A", "1 Year": "N/A",
                "5 Year": "N/A", "All Time": "N/A"
            }
    except Exception as e:
        print(f"Error fetching additional ETF data for {ticker}: {e}")
        return {
            "1 Day": "N/A", "5 Days": "N/A", "1 Month": "N/A",
            "6 Month": "N/A", "YTD": "N/A", "1 Year": "N/A",
            "5 Year": "N/A", "All Time": "N/A"
        }

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(data, columns=["Ticker", "Price", "Yield %", "Annual Dividend", "Ex Dividend Date", "Frequency", "Dividend Growth %"])

    # Get additional data for each ticker, attempting ETF path if stock path fails
    additional_data = []
    for ticker in df["Ticker"]:
        # Attempt to fetch ETF data first
        additional_etf_data = get_additional_etf_data(ticker.strip())
        if all(value == "N/A" for value in additional_etf_data.values()):
            # If ETF data is not available, fallback to stock data
            additional_data.append(get_additional_etf_data(ticker.strip()))
        else:
            additional_data.append(additional_etf_data)

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
