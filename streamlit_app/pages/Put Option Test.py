import streamlit as st

def calculate_long_put_profit(stock_price, strike_price, option_cost, contracts):
    value_at_expiry = max(strike_price - stock_price, 0)
    profit = (value_at_expiry - option_cost) * contracts * 100
    breakeven_price = strike_price - option_cost
    return value_at_expiry, profit, breakeven_price

st.title("Long Put Options Calculator")

# Input fields
stock_price = st.number_input("Current Stock Price ($)", min_value=0.0, step=0.01)
strike_price = st.number_input("Strike Price ($)", min_value=0.0, step=0.01)
option_cost = st.number_input("Option Cost ($)", min_value=0.0, step=0.01)
contracts = st.number_input("Number of Contracts", min_value=1, step=1)

if st.button("Calculate"):
    value_at_expiry, profit, breakeven_price = calculate_long_put_profit(stock_price, strike_price, option_cost, contracts)

    st.write(f"Value at Expiry: ${value_at_expiry:.2f}")
    st.write(f"Profit: ${profit:.2f}")
    st.write(f"Breakeven Price: ${breakeven_price:.2f}")
