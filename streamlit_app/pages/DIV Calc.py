import streamlit as st
import yfinance as yf
from datetime import datetime

# Title and date input
st.title(" DivFinancial Dashboard")
today_date = st.date_input("Today's Date", datetime.now())

# Ticker input and data fetching
ticker_input = st.text_input("Enter Stock Ticker", value='ABR')

# Fetching data
stock = yf.Ticker(ticker_input)
info = stock.info

# Safe fetching of stock information
current_price = info.get('regularMarketPrice', "Data not available")
if current_price == "Data not available":
    st.error("Failed to fetch current price.")

latest_dividend = info.get('lastDividendValue', "Data not available")
if latest_dividend == "Data not available":
    st.error("Failed to fetch latest dividend.")

st.write(f"Current Price for {ticker_input}: ${current_price}")
st.write(f"Latest Dividend Payment for {ticker_input}: ${latest_dividend}")

# Financial calculations input
average_cost_share = st.number_input("Average Cost Share", value=13.13)
quantity = st.number_input("Quantity", value=76)

# Calculations
if isinstance(current_price, (int, float)) and isinstance(average_cost_share, (int, float)):
    cost_value = average_cost_share * quantity
    market_value = current_price * quantity
    profit_loss = market_value - cost_value
    st.write("Cost Value: ", cost_value)
    st.write("Market Value: ", market_value)
    st.write("Profit (Loss): ", profit_loss)

    if isinstance(latest_dividend, (int, float)) and latest_dividend > 0:
        quarters_to_recovery = profit_loss / (latest_dividend * quantity)
        st.write("Quarters to Recovery: ", round(quarters_to_recovery, 2))
    else:
        st.write("Dividend data not available or dividend is zero, cannot calculate quarters to recovery.")
else:
    st.write("Missing or invalid data, cannot perform financial calculations.")