import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from lxml import html

def get_stock_data(tickers, past_days):
    data = {}
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.Timedelta(days=past_days)
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        data[ticker] = hist
    return data

def get_dividend_info(ticker):
    urls = [
        f"https://stockanalysis.com/etf/{ticker}/dividend/",
        f"https://stockanalysis.com/stocks/{ticker}/dividend/"
    ]
    for url in urls:
        response = requests.get(url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            dividend_xpath = '/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div'
            apy_xpath = '/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[1]/div'
            dividend = tree.xpath(dividend_xpath)
            apy = tree.xpath(apy_xpath)
            if dividend and apy:
                return dividend[0].text_content(), apy[0].text_content()
    return "N/A", "N/A"

def plot_stock_data(data):
    for ticker, hist in data.items():
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Close Price'))
        annual_dividend, apy = get_dividend_info(ticker)
        fig.update_layout(
            title=f"{ticker} - Annual Dividend: {annual_dividend}, APY: {apy}",
            xaxis_title='Date',
            yaxis_title='Price',
            template='plotly_white'
        )
        st.plotly_chart(fig)

st.title("Interactive Stock Charts with Dividend Yield (Annual Dividend and APY)")

tickers_input = st.text_area("Tickers Entry Box (separated by commas)", "AAPL, MSFT, GOOG")
past_days = st.number_input("Past days from today", min_value=1, value=90)

tickers = [ticker.strip() for ticker in tickers_input.split(",")]

if st.button("Generate Charts"):
    data = get_stock_data(tickers, past_days)
    plot_stock_data(data)
