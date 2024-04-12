import streamlit as st
import yfinance as yf
from datetime import datetime

# Title and date input
st.title("Stock Financial Dashboard")
today_date = st.date_input("Today's Date", datetime.now())

# Ticker input and data fetching
ticker_input = st.text_input("Enter Stock Ticker", value='ABR')
stock = yf.Ticker(ticker_input)
info = stock.info
current_price = info.get('regularMarketPrice', 0)
latest_dividend = info.get('lastDividendValue', 0)

# Display current stock data
st.write(f"Current Price for {ticker_input}: ${current_price}")
st.write(f"Latest Dividend Payment for {ticker_input}: ${latest_dividend}")

# Financial calculations input
average_cost_share = st.number_input("Average Cost Share", value=13.13)
quantity = st.number_input("Quantity", value=76)

# Calculations
cost_value = average_cost_share * quantity
market_value = current_price * quantity
profit_loss = market_value - cost_value
quarters_to_recovery = profit_loss / (latest_dividend * quantity) if latest_dividend > 0 else 'Dividend is zero'

# Displaying results
st.write("Cost Value: ", cost_value)
st.write("Market Value: ", market_value)
st.write("Profit (Loss): ", profit_loss)
if isinstance(quarters_to_recovery, str):
    st.write(quarters_to_recovery)
else:
    st.write("Quarters to Recovery: ", round(quarters_to_recovery, 2))