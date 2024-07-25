import streamlit as st
import pandas as pd

# Create a Streamlit app
st.title("TradingView Watchlist Viewer")

# Get the watchlist link from the user
watchlist_link = st.text_input("https://www.tradingview.com/watchlists/139248623/")

if watchlist_link:
    try:
        # Read the watchlist from the link
        watchlist_df = pd.read_html(watchlist_link)[0]
        st.write(watchlist_df)
    except Exception as e:
        st.error("Error parsing watchlist from the provided link. Please check if the link is correct.")
