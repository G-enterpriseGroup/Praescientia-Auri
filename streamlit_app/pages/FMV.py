import streamlit as st
import yfinance as yf
import pandas as pd

def fetch_financial_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Fetching required financial data
    pe_ratio = info.get('trailingPE', None)
    pb_ratio = info.get('priceToBook', None)
    ps_ratio = info.get('priceToSalesTrailing12Months', None)
    eps = info.get('trailingEps', None)
    book_value = info.get('bookValue', None)
    revenue_per_share = info.get('revenuePerShare', None)
    
    # Placeholder calculations for DDM and EV multiples
    ddm_value = None  # To be calculated with future dividend estimates
    ev_ebitda_multiple = None  # To be calculated with EBITDA values

    return {
        "Ticker": ticker,
        "P/E Ratio": pe_ratio,
        "P/B Ratio": pb_ratio,
        "P/S Ratio": ps_ratio,
        "EPS": eps,
        "Book Value": book_value,
        "Revenue Per Share": revenue_per_share,
        "DDM Value": ddm_value,
        "EV/EBITDA Multiple": ev_ebitda_multiple
    }

def calculate_valuation_metrics(tickers):
    financial_data = []
    for ticker in tickers:
        data = fetch_financial_data(ticker)
        financial_data.append(data)
    
    df = pd.DataFrame(financial_data)
    return df

# Streamlit app
st.title("Stock Valuation Metrics")

# Input for tickers
tickers_input = st.text_input("Enter stock tickers separated by commas:", "AAPL,MSFT,GOOGL")
tickers = [ticker.strip() for ticker in tickers_input.split(',')]

if st.button("Calculate Valuation Metrics"):
    valuation_df = calculate_valuation_metrics(tickers)
    st.dataframe(valuation_df)
