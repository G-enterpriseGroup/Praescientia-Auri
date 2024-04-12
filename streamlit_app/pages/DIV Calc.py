import streamlit as st
from datetime import datetime

# Input section with editable spaces
st.title("Financial Dashboard")
st.write("Today's Date:")
today_date = st.date_input("Date", datetime(2024, 4, 12))
average_cost_share = st.number_input("Average Cost Share", value=13.13)
abr = st.number_input("ABR", value=12.2)
dividend_payout = st.number_input("Dividend Payout", value=0.43)
quantity = st.number_input("Quantity", value=76)

# Calculations
cost_value = average_cost_share * quantity
market_value = abr * quantity
profit_loss = market_value - cost_value
quarters_to_recovery = profit_loss / (dividend_payout * quantity)

# Displaying results
st.write("Cost Value: ", cost_value)
st.write("Market Value: ", market_value)
st.write("Profit (Loss): ", profit_loss)
st.write("Quarters to Recovery: ", round(quarters_to_recovery, 2))