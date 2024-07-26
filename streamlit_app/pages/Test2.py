import streamlit as st
import requests
from bs4 import BeautifulSoup

def fetch_tickers(url):
    response = requests.get(url)
    html = response.text

    start = html.find('"symbols":[') + len('"symbols":[')
    end = html.find(']', start)
    symbols_str = html[start:end]
    symbols = [symbol.split(":")[1].strip('"') for symbol in symbols_str.split(',')]

    return symbols

# URL of the HTML file
url = 'https://www.tradingview.com/watchlists/139248623/'  # Replace with the actual URL of your HTML file

st.title("Ticker List")
st.write("Fetching tickers from HTML file...")

tickers = fetch_tickers(url)

if tickers:
    st.write("Tickers found:")
    tickers_str = ", ".join(tickers)
    st.write(tickers_str)
else:
    st.write("No tickers found.")
