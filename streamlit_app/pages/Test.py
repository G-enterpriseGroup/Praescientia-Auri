import streamlit as st
import pandas as pd
import requests
from lxml import html
from st_aggrid import AgGrid, GridOptionsBuilder

# Function to get stock data
def get_stock_data(ticker):
    base_url = "https://stockanalysis.com"
    etf_url = f"{base_url}/etf/{ticker}/dividend/"
    stock_url = f"{base_url}/stocks/{ticker}/dividend/"
    
    try:
        response = requests.get(etf_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            price = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
            yield_percent = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[1]/div/text()')[0]
            return {"Ticker": ticker, "Price": price, "Yield %": yield_percent}
        else:
            response = requests.get(stock_url)
            if response.status_code == 200:
                tree = html.fromstring(response.content)
                price = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')[0]
                yield_percent = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[1]/div/text()')[0]
                return {"Ticker": ticker, "Price": price, "Yield %": yield_percent}
            else:
                return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A"}
    except:
        return {"Ticker": ticker, "Price": "N/A", "Yield %": "N/A"}

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

# Fetch data for each ticker
if tickers:
    data = [get_stock_data(ticker.strip()) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(data)
    
    # Build grid options
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, filterable=True)
    gb.configure_grid_options(domLayout='autoHeight', ensureDomOrder=True)
    gridOptions = gb.build()
    
    # Display DataFrame using AgGrid
    AgGrid(df, gridOptions=gridOptions, height=500, width='100%', theme='light')

# Adjust the width of the page
st.markdown(
    """
    <style>
    .reportview-container .main .block-container{
        max-width: 80%;
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
