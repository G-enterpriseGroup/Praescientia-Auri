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
url2 = 'https://www.tradingview.com/watchlists/158296099/'

st.title("G-EnterpriseGroup Trading List")

def display_tickers(url, button_key):
    st.write("Fetching tickers from G-EnterpriseGroup Database:")

    if st.session_state.get(button_key, False):
        # Fetch tickers only if the button was pressed
        tickers = fetch_tickers(url)
        st.session_state[button_key] = False  # Reset the button state
    else:
        tickers = []

    cleaned_tickers = clean_tickers(tickers)

    if cleaned_tickers:
        st.write("Tickers found:")
        tickers_str = ", ".join(cleaned_tickers)
        st.write(tickers_str)

        # Copy button
        copy_button = f"""
        <button onclick="navigator.clipboard.writeText('{tickers_str}')">Copy Tickers</button>
        """
        components.html(copy_button)

    else:
        st.write("No tickers found.")

    # Refresh button
    if st.button("Refresh", key=button_key):
        st.session_state[button_key] = True  # Set the button state to refresh

# Initialize session state
if 'refresh_red' not in st.session_state:
    st.session_state['refresh_red'] = True  # Initialize to fetch on first load
if 'refresh_banks' not in st.session_state:
    st.session_state['refresh_banks'] = True  # Initialize to fetch on first load

# Display tickers for URL 1
with st.expander("Tickers from List - Red"):
    display_tickers(url1, "refresh_red")

# Display tickers for URL 2
with st.expander("Tickers from List - Banks"):
    display_tickers(url2, "refresh_banks")
