import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime

# Set Streamlit page configuration
st.set_page_config(page_title="Stock and ETF Dashboard", layout="wide")

# Function to calculate performance data
def calculate_performance(ticker):
    try:
        ticker_data = yf.Ticker(ticker)
        hist = ticker_data.history(period="1y")

        if not hist.empty:
            # Get current and past prices for performance calculations
            last_close = hist["Close"][-1]
            day_ago = hist["Close"][-2] if len(hist) > 1 else None
            five_days_ago = hist["Close"][-6] if len(hist) > 5 else None
            one_month_ago = hist["Close"][-22] if len(hist) > 22 else None
            six_months_ago = hist["Close"][0] if len(hist) > 0 else None

            # Calculate percentage changes
            performance = {
                "1 Day": f"{((last_close - day_ago) / day_ago) * 100:.2f}%" if day_ago else "N/A",
                "5 Days": f"{((last_close - five_days_ago) / five_days_ago) * 100:.2f}%" if five_days_ago else "N/A",
                "1 Month": f"{((last_close - one_month_ago) / one_month_ago) * 100:.2f}%" if one_month_ago else "N/A",
                "6 Month": f"{((last_close - six_months_ago) / six_months_ago) * 100:.2f}%" if six_months_ago else "N/A",
                "YTD": "N/A",  # Customize for Year-to-Date
                "1 Year": f"{((last_close - hist['Close'][0]) / hist['Close'][0]) * 100:.2f}%" if len(hist) > 0 else "N/A",
                "5 Year": "N/A",  # Extend for longer data
                "All Time": "N/A",  # Extend for longer data
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

        # Convert ex-dividend date if available
        if ex_dividend_date != "N/A":
            ex_dividend_date = datetime.utcfromtimestamp(ex_dividend_date).strftime("%Y-%m-%d")

        # Get performance data
        performance = calculate_performance(ticker)

        return {
            "Name": long_name,
            "Ticker": ticker,
            "Price": f"${price:.2f}" if price != "N/A" else "N/A",
            "Yield %": f"{yield_percent * 100:.2f}%" if yield_percent != "N/A" else "N/A",
            "Annual Dividend": f"${annual_dividend:.2f}" if annual_dividend != "N/A" else "N/A",
            "Ex Dividend Date": ex_dividend_date,
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
