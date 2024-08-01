import streamlit as st
import pandas as pd
import requests
from lxml import html

# Function to get stock data
def get_stock_data(ticker, html_file_path=None):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    tradingview_url = f"https://www.tradingview.com/symbols/NYSE-{ticker}/"

    try:
        # Attempt to get data from stockanalysis.com
        response = requests.get(etf_url)
        if response.status_code != 200:
            response = requests.get(stock_url)

        if response.status_code == 200:
            tree = html.fromstring(response.content)
            price = tree.xpath('//*[@id="main"]/div[1]/div[2]/div/div[1]/text()')
            yield_percent = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[1]/div/text()')
            annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')
            ex_dividend_date = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[3]/div/text()')
            frequency = tree.xpath('//*[@id="main"]/div[2]/div/div[2]/div[4]/div/text()')
            dividend_growth = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[6]/div/text()')

            price = price[0] if price else "N/A"
            yield_percent = yield_percent[0] if yield_percent else "N/A"
            annual_dividend = annual_dividend[0] if annual_dividend else "N/A"
            ex_dividend_date = ex_dividend_date[0] if ex_dividend_date else "N/A"
            frequency = frequency[0] if frequency else "N/A"
            dividend_growth = dividend_growth[0] if dividend_growth else "N/A"
        else:
            price = yield_percent = annual_dividend = ex_dividend_date = frequency = dividend_growth = "N/A"

        # Get additional data from TradingView if HTML file is provided
        if html_file_path:
            try:
                # Load and parse the HTML content
                with open(html_file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                tree = html.fromstring(content)

                # Define XPaths for each return period
                return_xpaths = {
                    "1 Day": '//*[@class="contentBox-1gjuTnJ7"]/div[2]/div/div[1]/span[2]/text()',
                    "5 Days": '//*[@class="contentBox-1gjuTnJ7"]/div[3]/div/div[1]/span[2]/text()',
                    "1 Month": '//*[@class="contentBox-1gjuTnJ7"]/div[4]/div/div[1]/span[2]/text()',
                    "6 Months": '//*[@class="contentBox-1gjuTnJ7"]/div[5]/div/div[1]/span[2]/text()',
                    "YTD": '//*[@class="contentBox-1gjuTnJ7"]/div[6]/div/div[1]/span[2]/text()',
                    "1 Year": '//*[@class="contentBox-1gjuTnJ7"]/div[7]/div/div[1]/span[2]/text()',
                    "5 Years": '//*[@class="contentBox-1gjuTnJ7"]/div[8]/div/div[1]/span[2]/text()',
                    "All Time": '//*[@class="contentBox-1gjuTnJ7"]/div[9]/div/div[1]/span[2]/text()'
                }

                # Extract return data
                returns = {period: (tree.xpath(xpath)[0] if tree.xpath(xpath) else "N/A") for period, xpath in return_xpaths.items()}

            except Exception as e:
                st.error(f"An error occurred while processing the HTML file for {ticker}: {str(e)}")
                returns = {period: "N/A" for period in return_xpaths.keys()}

        else:
            # If no HTML file provided, fetch data directly from TradingView URL
            response_tv = requests.get(tradingview_url)
            if response_tv.status_code == 200:
                tree_tv = html.fromstring(response_tv.content)
                returns = {
                    "1 Day": tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[1]/span/span[2]/text()'),
                    "5 Days": tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[2]/span/span[2]/text()'),
                    "1 Month": tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[3]/span/span[2]/text()'),
                    "6 Month": tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[4]/span/span[2]/text()'),
                    "YTD": tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[5]/span/span[2]/text()'),
                    "1 Year": tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[6]/span/span[2]/text()'),
                    "5 Year": tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[7]/span/span[2]/text()'),
                    "All Time": tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[8]/span/span[2]/text()')
                }
                returns = {k: (v[0] if v else "N/A") for k, v in returns.items()}
            else:
                returns = {period: "N/A" for period in ["1 Day", "5 Days", "1 Month", "6 Month", "YTD", "1 Year", "5 Year", "All Time"]}

        return {
            "Ticker": ticker,
            "Price": price,
            "Yield %": yield_percent,
            "Annual Dividend": annual_dividend,
            "Ex Dividend Date": ex_dividend_date,
            "Frequency": frequency,
            "Dividend Growth %": dividend_growth,
            **returns
        }
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return {
            "Ticker": ticker,
            "Price": "N/A",
            "Yield %": "N/A",
            "Annual Dividend": "N/A",
            "Ex Dividend Date": "N/A",
            "Frequency": "N/A",
            "Dividend Growth %": "N/A",
            "1 Day": "N/A",
            "5 Days": "N/A",
            "1 Month": "N/A",
            "6 Month": "N/A",
            "YTD": "N/A",
            "1 Year": "N/A",
            "5 Year": "N/A",
            "All Time": "N/A"
        }

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    # Specify the HTML file path (update this path if necessary)
    html_file_path = "/mnt/data/SCM Stock Price and Chart — NYSE_SCM — TradingView.html"
    
    data = [get_stock_data(ticker.strip(), html_file_path) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(data)
    
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
