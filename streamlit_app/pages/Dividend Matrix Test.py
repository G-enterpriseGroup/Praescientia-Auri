import yfinance as yf
import pandas as pd
import streamlit as st

# Set Streamlit page configuration
st.set_page_config(page_title="Stock and ETF Dashboard", layout="wide")

# Function to fetch stock and ETF data
def fetch_stock_data(ticker):
    try:
        ticker_data = yf.Ticker(ticker)
        long_name = ticker_data.info.get("longName", "N/A")
        price = ticker_data.history(period="1d")["Close"][-1] if not ticker_data.history(period="1d").empty else "N/A"
        yield_percent = ticker_data.info.get("dividendYield", "N/A")
        annual_dividend = ticker_data.info.get("dividendRate", "N/A")
        ex_dividend_date = ticker_data.info.get("exDividendDate", "N/A")
        frequency = "Quarterly" if ticker_data.info.get("dividendFrequency", 1) == 4 else "Monthly"  # Adjust based on known frequencies

        return {
            "Name": long_name,
            "Ticker": ticker,
            "Price": f"${price:.2f}" if price != "N/A" else "N/A",
            "Yield %": f"{yield_percent * 100:.2f}%" if yield_percent != "N/A" else "N/A",
            "Annual Dividend": f"${annual_dividend:.2f}" if annual_dividend != "N/A" else "N/A",
            "Ex Dividend Date": pd.to_datetime(ex_dividend_date).strftime("%Y-%m-%d") if ex_dividend_date != "N/A" else "N/A",
            "Frequency": frequency,
        }
    except Exception as e:
        return {
            "Name": "N/A",
            "Ticker": ticker,
            "Price": "N/A",
            "Yield %": "N/A",
            "Annual Dividend": "N/A",
            "Ex Dividend Date": "N/A",
            "Frequency": "N/A",
        }

# Streamlit App
st.title("Stock and ETF Dashboard")

# Input for tickers
tickers = st.text_input("Enter tickers separated by commas").split(',')

if tickers:
    # Process tickers
    data = [fetch_stock_data(ticker.strip().upper()) for ticker in tickers if ticker.strip()]
    df = pd.DataFrame(data)

    # Display data in Streamlit
    st.write(df)

    # Optional: Adjust page width and table styling
    st.markdown(
        """
        <style>
        .reportview-container .main .block-container {
            max-width: 100%;
            padding: 2rem;
        }
        table {
            width: 100% !important;
            table-layout: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
