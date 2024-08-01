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

        # Get additional data from TradingView
        response_tv = requests.get(tradingview_url)
        if response_tv.status_code == 200:
            tree_tv = html.fromstring(response_tv.content)
            day_1 = tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[1]/span/span[2]/text()')
            days_5 = tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[2]/span/span[2]/text()')
            month_1 = tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[3]/span/span[2]/text()')
            month_6 = tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[4]/span/span[2]/text()')
            ytd = tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[5]/span/span[2]/text()')
            year_1 = tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[6]/span/span[2]/text()')
            year_5 = tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[7]/span/span[2]/text()')
            all_time = tree_tv.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[8]/span/span[2]/text()')
            
            day_1 = day_1[0] if day_1 else "N/A"
            days_5 = days_5[0] if days_5 else "N/A"
            month_1 = month_1[0] if month_1 else "N/A"
            month_6 = month_6[0] if month_6 else "N/A"
            ytd = ytd[0] if ytd else "N/A"
            year_1 = year_1[0] if year_1 else "N/A"
            year_5 = year_5[0] if year_5 else "N/A"
            all_time = all_time[0] if all_time else "N/A"
        else:
            day_1 = days_5 = month_1 = month_6 = ytd = year_1 = year_5 = all_time = "N/A"

        return {
            "Ticker": ticker,
            "Price": price,
            "Yield %": yield_percent,
            "Annual Dividend": annual_dividend,
            "Ex Dividend Date": ex_dividend_date,
            "Frequency": frequency,
            "Dividend Growth %": dividend_growth,
            "1 Day": day_1,
            "5 Days": days_5,
            "1 Month": month_1,
            "6 Month": month_6,
            "YTD": ytd,
            "1 Year": year_1,
            "5 Year": year_5,
            "All Time": all_time
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
