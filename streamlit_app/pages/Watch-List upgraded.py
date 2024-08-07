import streamlit as st
import requests
import json
import streamlit.components.v1 as components

def fetch_tickers(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors

        # Use BeautifulSoup to parse the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the relevant JavaScript containing the tickers
        script = soup.find('script', text=lambda t: '"symbols":[' in t)
        if not script:
            return []

        # Extract JSON-like part of the script
        start = script.text.find('"symbols":[') + len('"symbols":[')
        end = script.text.find(']', start)
        symbols_str = script.text[start:end]
        symbols = json.loads(f'[{symbols_str}]')  # Convert to JSON list

        return symbols

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from {url}: {e}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Error parsing ticker data: {e}")
        return []

def clean_tickers(tickers):
    return [ticker.split(':')[1] if ':' in ticker else ticker for ticker in tickers]

# URL of the HTML files
url1 = 'https://www.tradingview.com/watchlists/139248623/'
url2 = 'https://www.tradingview.com/watchlists/158296099/'

st.title("G-EnterpriseGroup Trading List")

def display_tickers(url):
    st.write("Fetching tickers from G-EnterpriseGroup Database:")

    tickers = fetch_tickers(url)
    cleaned_tickers = clean_tickers(tickers)

    if cleaned_tickers:
        st.write("Tickers found:")
        tickers_str = ",".join(cleaned_tickers)  # No spaces between tickers
        st.write(tickers_str)

        copy_button = f"""
        <button onclick="navigator.clipboard.writeText('{tickers_str}')">Copy Tickers</button>
        """
        components.html(copy_button)
    else:
        st.write("No tickers found.")

# Display tickers for URL 1
with st.expander("Tickers from List - Red"):
    display_tickers(url1)

# Display tickers for URL 2
with st.expander("Tickers from List - Banks"):
    display_tickers(url2)

# Add a refresh button
if st.button("Refresh"):
    st.experimental_rerun()
