import requests
from bs4 import BeautifulSoup
import streamlit as st

def get_tradingview_watchlist(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    tickers = []

    for ticker in soup.find_all('div', class_='tv-symbol-name'):
        tickers.append(ticker.text.strip())

    return tickers

# Replace with your TradingView watchlist URL
watchlist_url = 'https://www.tradingview.com/watchlists/139248623/'

# Fetch tickers
tickers = get_tradingview_watchlist(watchlist_url)

# Streamlit app
st.title('TradingView Watchlist')
if tickers:
    st.write(tickers)
else:
    st.write("No tickers found or unable to access the watchlist.")
