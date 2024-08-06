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

# URL of the HTML file
url = 'https://www.tradingview.com/watchlists/139248623/'  # Replace with the actual URL of your HTML file

st.title("Raj's Trading View Red List")
st.write("Fetching tickers from file...")

if st.button('Refresh'):
    tickers = fetch_tickers(url)
    st.session_state.cleaned_tickers = clean_tickers(tickers)

if 'cleaned_tickers' not in st.session_state:
    tickers = fetch_tickers(url)
    st.session_state.cleaned_tickers = clean_tickers(tickers)

if st.session_state.cleaned_tickers:
    st.write("Tickers found:")
    tickers_str = ", ".join(st.session_state.cleaned_tickers)
    st.write(tickers_str)
    
    # Add a button to copy the tickers to the clipboard
    copy_button = f"""
    <button onclick="navigator.clipboard.writeText('{tickers_str}')">Copy Tickers</button>
    """
    components.html(copy_button)
else:
    st.write("No tickers found.")

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
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

# URL of the HTML file
url = 'https://www.tradingview.com/watchlists/139248623/'  # Replace with the actual URL of your HTML file

st.title("Raj's Trading View Red List")
st.write("Fetching tickers from file...")

if st.button('Refresh'):
    tickers = fetch_tickers(url)
    st.session_state.cleaned_tickers = clean_tickers(tickers)

if 'cleaned_tickers' not in st.session_state:
    tickers = fetch_tickers(url)
    st.session_state.cleaned_tickers = clean_tickers(tickers)

if st.session_state.cleaned_tickers:
    st.write("Tickers found:")
    tickers_str = ", ".join(st.session_state.cleaned_tickers)
    st.write(tickers_str)
    
    # Add a button to copy the tickers to the clipboard
    copy_button = f"""
    <button onclick="navigator.clipboard.writeText('{tickers_str}')">Copy Tickers</button>
    """
    components.html(copy_button)
else:
    st.write("No tickers found.")
