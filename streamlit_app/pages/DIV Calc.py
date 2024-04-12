import streamlit as st
import yfinance as yf
from datetime import datetime

# Title and date input
st.title("DivFinancial Dashboard")
today_date = st.date_input("Today's Date", datetime.now())

# Ticker input and data fetching
ticker_input = st.text_input("Enter Stock Ticker", value='ABR')

def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")['Close'].iloc[-1]  # Latest stock price
    dividends = stock.dividends.tail(1).values  # Fetching latest dividend payout as array
    dividend = dividends[0] if len(dividends) > 0 else 0  # Handling no dividend case
    return price, dividend

latest_price, latest_dividend = get_stock_data(ticker_input)
st.write(f"Current Price for {ticker_input}: ${latest_price}")
st.write(f"Latest Dividend Payment for {ticker_input}: ${latest_dividend}")

# Financial calculations input
average_cost_per_share = st.number_input("Average Cost Per Share", value=13.13)
quantity = st.number_input("Quantity", value=76)

# Calculations
if isinstance(latest_price, (int, float)) and isinstance(average_cost_per_share, (int, float)):
    cost_value = average_cost_per_share * quantity
    market_value = latest_price * quantity
    profit_loss = market_value - cost_value
    st.write(f"Cost Value: ${cost_value}")
    st.write(f"Market Value: ${market_value}")
    st.write(f"Profit (Loss): ${profit_loss}")

    if isinstance(latest_dividend, (int, float)) and latest_dividend > 0:
        quarters_to_recovery = profit_loss / (latest_dividend * quantity)
        st.write(f"Quarters to Recovery: {round(quarters_to_recovery, 2)}")
    else:
        st.write("Dividend data not available or dividend is zero, cannot calculate quarters to recovery.")
else:
    st.write("Missing or invalid data, cannot perform financial calculations.")