import streamlit as st
import yfinance as yf
import pandas as pd

def fetch_last_dividend_dates(ticker):
    stock = yf.Ticker(ticker)
    dividends = stock.dividends
    if dividends.empty:
        return None
    # Filtering dividends from the last 12 months
    end_date = pd.Timestamp.today()
    start_date = end_date - pd.DateOffset(months=12)
    filtered_dividends = dividends[(dividends.index >= start_date) & (dividends.index <= end_date)]
    # Group by year and month, get the last date
    monthly_last_div = filtered_dividends.groupby([filtered_dividends.index.year, filtered_dividends.index.month]).last()
    return monthly_last_div

st.title('Monthly Last Ex-Dividend Dates')

ticker = st.text_input('Enter Ticker Symbol', 'PULS')
if ticker:
    last_dividends = fetch_last_dividend_dates(ticker)
    if last_dividends is not None:
        st.write("Last ex-dividend date for each of the last 12 months:")
        for date, value in last_dividends.items():
            st.write(f"{date}: {value}")
    else:
        st.write("No dividends found in the last 12 months for this ticker.")

