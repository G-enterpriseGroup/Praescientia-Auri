import streamlit as st
import pandas as pd
import requests
from lxml import html
import yfinance as yf

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    
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
            returns = get_returns(ticker)
            return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth, **returns}
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
                returns = get_returns(ticker)
                return {"Ticker": ticker, "Price": price, "Yield %": yield_percent, "Annual Dividend": annual_dividend, "Ex Dividend Date": ex_dividend_date, "Frequency": frequency, "Dividend Growth %": dividend_growth, **returns}
            else:
                return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A", **get_returns(ticker, fallback=True)}
    except Exception as e:
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A", "Annual Dividend": "N/A", "Ex Dividend Date": "N/A", "Frequency": "N/A", "Dividend Growth %": "N/A", **get_returns(ticker, fallback=True)}

# Function to get stock returns using yfinance
def get_returns(ticker, fallback=False):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5y")
        
        if not hist.empty:
            returns = {
                "1 month": f"{((hist['Close'][-1] - hist['Close'][-22]) / hist['Close'][-22] * 100):.2f}%" if len(hist) > 22 else "N/A",
                "3 months": f"{((hist['Close'][-1] - hist['Close'][-66]) / hist['Close'][-66] * 100):.2f}%" if len(hist) > 66 else "N/A",
                "6 months": f"{((hist['Close'][-1] - hist['Close'][-132]) / hist['Close'][-132] * 100):.2f}%" if len(hist) > 132 else "N/A",
                "1 year": f"{((hist['Close'][-1] - hist['Close'][-252]) / hist['Close'][-252] * 100):.2f}%" if len(hist) > 252 else "N/A",
                "5 years": f"{((hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0] * 100):.2f}%" if len(hist) > 0 else "N/A",
                "all": f"{((hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0] * 100):.2f}%" if len(hist) > 0 else "N/A",
            }
            return returns
        else:
            return {
                "1 month": "N/A",
                "3 months": "N/A",
                "6 months": "N/A",
                "1 year": "N/A",
                "5 years": "N/A",
                "all": "N/A"
            }
    except Exception as e:
        return {
            "1 month": "N/A",
            "3 months": "N/A",
            "6 months": "N/A",
            "1 year": "N/A",
            "5 years": "N/A",
            "all": "N/A"
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
