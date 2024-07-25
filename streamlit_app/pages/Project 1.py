import streamlit as st
import pandas as pd

# URL of the TradingView watchlist
url = 'https://www.tradingview.com/watchlists/139248623/'

# Read the HTML content of the watchlist page
watchlist_data = pd.read_html(url)

# Extract the table data (assuming the table with ticker information is the first table on the page)
watchlist_df = watchlist_data[0]

# Display the watchlist data in a table
st.write(watchlist_df)
