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
    company_names = {}
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.Timedelta(days=past_days)
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            if not hist.empty:
                data[ticker] = hist
                company_names[ticker] = stock.info['longName']  # Get company name
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
    return data, company_names

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

def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def plot_stock_data(data, company_names):
    num_tickers = len(data)
    num_cols = 2
    num_rows = math.ceil(num_tickers / num_cols)
    
    fig = make_subplots(rows=num_rows*2, cols=num_cols, 
                        subplot_titles=[f"{company_names[ticker]} ({ticker}) - Annual Dividend: {get_dividend_info(ticker)[0]}, APY: {get_dividend_info(ticker)[1]}" for ticker in data.keys()],
                        shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3] * num_rows)

    row = 1
    col = 1

    for ticker, hist in data.items():
        # Plot closing price
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name=f'{ticker} Price'), row=row, col=col)
        
        # Calculate and plot RSI
        rsi = calculate_rsi(hist)
        fig.add_trace(go.Scatter(x=hist.index, y=rsi, mode='lines', name=f'{ticker} RSI', line=dict(color='red')), row=row+1, col=col)
        
        if col == num_cols:
            row += 2  # Increment by 2 to add RSI below the stock chart
            col = 1
        else:
            col += 1

    fig.update_layout(height=600*num_rows, width=1200, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.title("Interactive Stock Charts with Dividend Yield and RSI")

tickers_input = st.text_area("Tickers Entry Box (separated by commas)", " ")
past_days = st.number_input("Past days from today", min_value=1, value=90)

tickers = [ticker.strip() for ticker in tickers_input.split(",")]

if st.button("Generate Charts"):
    data, company_names = get_stock_data(tickers, past_days)
    if data:
        plot_stock_data(data, company_names)
    else:
        st.error("No data available for the given tickers and date range.")
