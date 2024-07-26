import streamlit as st
import streamlit.components.v1 as components

# URL to your TradingView watchlist
tradingview_url = "https://www.tradingview.com/watchlists/139248623/"

# Embed the TradingView watchlist using an iframe
iframe_code = f"""
<iframe src="{tradingview_url}" width="100%" height="600px" frameborder="0" allowfullscreen></iframe>
"""

# Display the TradingView widget
components.html(iframe_code, height=600)
