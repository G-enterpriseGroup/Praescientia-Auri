import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from lxml import html
import math

# Set Streamlit to always run in wide mode
st.set_page_config(layout="wide")

def get_stock_data(tickers, past_days):
    data = {}
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.Timedelta(days=past_days)
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            if not hist.empty:
                hist['HA_Close'] = (hist['Open'] + hist['Close'] + hist['High'] + hist['Low']) / 4
                hist['HA_Open'] = (hist['Open'] + hist['Close']) / 2
                for i in range(1, len(hist)):
                    hist['HA_Open'].iloc[i] = (hist['HA_Open'].iloc[i-1] + hist['HA_Close'].iloc[i-1]) / 2
                hist['HA_High'] = hist[['High', 'HA_Open', 'HA_Close']].max(axis=1)
                hist['HA_Low'] = hist[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
                data[ticker] = hist
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
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
    num_tickers = len(data)
    num_cols = 2
    num_rows = math.ceil(num_tickers / num_cols)
    
    fig = make_subplots(rows=num_rows, cols=num_cols, subplot_titles=[f"{ticker} - Annual Dividend: {get_dividend_info(ticker)[0]}, APY: {get_dividend_info(ticker)[1]}" for ticker in data.keys()])

    row = 1
    col = 1

    for ticker, hist in data.items():
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['HA_Open'],
            high=hist['HA_High'],
            low=hist['HA_Low'],
            close=hist['HA_Close'],
            name=ticker), row=row, col=col)
        if col == num_cols:
            row += 1
            col = 1
        else:
            col += 1

    fig.update_layout(height=300*num_rows, width=1200, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.title("Interactive Heikin Ashi Stock Charts with Dividend Yield (Annual Dividend and APY)")

tickers_input = st.text_area("Tickers Entry Box (separated by commas)", "BXMT, MFA, SCM, PUTW, PFRL, CLOZ, TYLG, PULS, MFC, IAUF, SPYI, ZIVB")
past_days = st.number_input("Past days from today", min_value=1, value=90)

tickers = [ticker.strip() for ticker in tickers_input.split(",")]

if st.button("Generate Charts"):
    data = get_stock_data(tickers, past_days)
    if data:
        plot_stock_data(data)
    else:
        st.error("No data available for the given tickers and date range.")
