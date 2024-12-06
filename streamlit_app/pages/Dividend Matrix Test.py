import yfinance as yf
import pandas as pd
import streamlit as st

# Set Streamlit page configuration
st.set_page_config(page_title="Stock and ETF Dashboard", layout="wide")

# Function to calculate performance data
def calculate_performance(ticker):
    try:
        ticker_data = yf.Ticker(ticker)
        hist = ticker_data.history(period="6mo")

        if not hist.empty:
            # Calculate returns
            last_close = hist["Close"][-1]
            performance = {
                "1 Day": f"{((last_close - hist['Close'][-2]) / hist['Close'][-2]) * 100:.2f}%" if len(hist) > 1 else "N/A",
                "5 Days": f"{((last_close - hist['Close'][-6]) / hist['Close'][-6]) * 100:.2f}%" if len(hist) > 5 else "N/A",
                "1 Month": f"{((last_close - hist['Close'][-22]) / hist['Close'][-22]) * 100:.2f}%" if len(hist) > 22 else "N/A",
                "6 Month": f"{((last_close - hist['Close'][0]) / hist['Close'][0]) * 100:.2f}%" if len(hist) > 0 else "N/A",
                "YTD": f"{((last_close - hist['Close'][0]) / hist['Close'][0]) * 100:.2f}%" if "YTD" in hist.columns else "N/A",
                "1 Year": f"{((last_close - hist['Close'][0]) / hist['Close'][0]) * 100:.2f}%" if len(hist) >= 252 else "N/A",  # Approx 252 trading days in a year
                "5 Year": "N/A",  # You can fetch this using longer history
                "All Time": f"{((last_close - hist['Close'][0]) / hist['Close'][0]) * 100:.2f}%" if len(hist) > 0 else "N/A",
            }
        else:
            performance = {
                "1 Day": "N/A",
                "5 Days": "N/A",
                "1 Month": "N/A",
                "6 Month": "N/A",
                "YTD": "N/A",
                "1 Year": "N/A",
                "5 Year": "N/A",
                "All Time": "N/A",
            }
        return performance
    except Exception as e:
        return {
            "1 Day": "N/A",
            "5 Days": "N/A",
            "1 Month": "N/A",
            "6 Month": "N/A",
            "YTD": "N/A",
            "1 Year": "N/A",
            "5 Year": "N/A",
            "All Time": "N/A",
        }

# Function to fetch stock and ETF data
def fetch_stock_data(ticker):
    try:
        ticker_data = yf.Ticker(ticker)
        long_name = ticker_data.info.get("longName", "N/A")
        price = ticker_data.history(period="1d")["Close"][-1] if not ticker_data.history(period="1d").empty else "N/A"
        yield_percent = ticker_data.info.get("dividendYield", "N/A")
        annual_dividend = ticker_data.info.get("dividendRate", "N/A")
        ex_dividend_date = ticker_data.info.get("exDividendDate", "N/A")
        frequency = "Quarterly" if ticker_data.info.get("dividendFrequency", 1) == 4 else "Monthly"

        # Ensure yield_percent is in percentage format
        yield_percent = f"{yield_percent * 100:.2f}%" if yield_percent != "N/A" else "N/A"

        # Get performance data
        performance = calculate_performance(ticker)

        return {
            "Name": long_name,
            "Ticker": ticker,
            "Price": f"${price:.2f}" if price != "N/A" else "N/A",
            "Yield %": yield_percent,
            "Annual Dividend": f"${annual_dividend:.2f}" if annual_dividend != "N/A" else "N/A",
            "Ex Dividend Date": pd.to_datetime(ex_dividend_date).strftime("%Y-%m-%d") if ex_dividend_date != "N/A" else "N/A",
            "Frequency": frequency,
            **performance,  # Include performance data
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
            "1 Day": "N/A",
            "5 Days": "N/A",
            "1 Month": "N/A",
            "6 Month": "N/A",
            "YTD": "N/A",
            "1 Year": "N/A",
            "5 Year": "N/A",
            "All Time": "N/A",
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
