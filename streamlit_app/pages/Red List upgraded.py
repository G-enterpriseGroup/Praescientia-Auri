import streamlit as st
import requests
from bs4 import BeautifulSoup
import streamlit.components.v1 as components

def fetch_tickers(url):
    response = requests.get(url)
    html = response.text

    start = html.find('"symbols":[') + len('"symbols":[')
    end = html.find(']', start)
    symbols_str = html[start:end]
    symbols = [symbol.strip('"') for symbol in symbols_str.split(',')]

    return symbols

def clean_tickers(tickers):
    return [ticker.split(':')[1] if ':' in ticker else ticker for ticker in tickers]

# URL of the HTML files
url1 = 'https://www.tradingview.com/watchlists/139248623/'
url2 = 'https://www.tradingview.com/watchlists/158248037/'

st.title("Raj's Trading View Red List")

def display_tickers(url):
    st.write(f"Fetching tickers from URL: {url}")

    tickers = fetch_tickers(url)
    cleaned_tickers = clean_tickers(tickers)

    if cleaned_tickers:
        st.write("Tickers found:")
        tickers_str = ", ".join(cleaned_tickers)
        st.write(tickers_str)

        copy_button = f"""
        <button onclick="navigator.clipboard.writeText('{tickers_str}')">Copy Tickers</button>
        """
        components.html(copy_button)
    else:
        st.write("No tickers found.")

# Display tickers for URL 1
with st.beta_expander("Tickers from URL 1"):
    display_tickers(url1)

# Display tickers for URL 2
with st.beta_expander("Tickers from URL 2"):
    display_tickers(url2)
