import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def fetch_etf_data(ticker):
    etf = yf.Ticker(ticker)
    
    # Get market price and NAV
    market_price = etf.history(period="1d")['Close'].iloc[0]
    nav = etf.info.get('navPrice', None)
    
    # Get expense ratio
    expense_ratio = etf.info.get('expenseRatio', None)

    # Get dividend yield
    dividend_yield = etf.info.get('yield', None)
    
    # Underlying holdings (for detailed analysis)
    holdings = etf.info.get('holdings', None)
    
    return {
        "Ticker": ticker,
        "Market Price": market_price,
        "NAV": nav,
        "Expense Ratio": expense_ratio,
        "Dividend Yield": dividend_yield,
        "Holdings": holdings
    }

def calculate_fair_value(etf_data):
    # Fair value based on NAV and expenses
    if etf_data['NAV'] is not None and etf_data['Expense Ratio'] is not None:
        adjusted_nav = etf_data['NAV'] * (1 - etf_data['Expense Ratio'])
    else:
        adjusted_nav = None
    
    return adjusted_nav

def display_etf_analysis(tickers):
    etf_analysis = []
    
    for ticker in tickers:
        etf_data = fetch_etf_data(ticker)
        fair_value = calculate_fair_value(etf_data)
        
        etf_analysis.append({
            "Ticker": etf_data['Ticker'],
            "Market Price": etf_data['Market Price'],
            "NAV": etf_data['NAV'],
            "Adjusted NAV (Fair Value)": fair_value,
            "Market Price vs NAV": (etf_data['Market Price'] / etf_data['NAV'] - 1) * 100 if etf_data['NAV'] is not None else None,
            "Expense Ratio": etf_data['Expense Ratio'],
            "Dividend Yield": etf_data['Dividend Yield'],
        })
    
    df = pd.DataFrame(etf_analysis)
    return df

# Streamlit app
st.title("ETF Fair Market Value Analysis")

# Input for tickers
tickers_input = st.text_input("Enter ETF tickers separated by commas:", "SPY,QQQ,VOO")
tickers = [ticker.strip() for ticker in tickers_input.split(',')]

if st.button("Analyze ETFs"):
    etf_analysis_df = display_etf_analysis(tickers)
    st.dataframe(etf_analysis_df)

    st.markdown("### Detailed Holdings")
    for ticker in tickers:
        etf = yf.Ticker(ticker)
        try:
            st.write(f"Holdings for {ticker}:")
            st.dataframe(pd.DataFrame(etf.info.get('holdings')))
        except:
            st.write(f"Unable to retrieve holdings for {ticker}.")
