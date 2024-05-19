import streamlit as st

# Inputs
total_investment = st.number_input('Total Investment', value=5000)
ask_price_premium = st.number_input('Ask Price Premium', value=1.3)
expected_stock_price = st.number_input('Expected Stock Price on June 3rd', value=49.51)
strike_price = st.number_input('Strike Price', value=54)

# Constants
shares_per_contract = 100

# Calculations
cost_per_contract = ask_price_premium * shares_per_contract
number_of_contracts = round(total_investment / cost_per_contract)
total_cost = number_of_contracts * cost_per_contract
intrinsic_value_per_share = expected_stock_price - strike_price
intrinsic_value_per_contract = intrinsic_value_per_share * shares_per_contract
total_intrinsic_value = intrinsic_value_per_contract * number_of_contracts
total_profit = total_intrinsic_value - total_cost
profit_per_contract = intrinsic_value_per_contract - cost_per_contract

# Display results
st.write(f"Cost per Contract: {cost_per_contract}")
st.write(f"Number of Contracts: {number_of_contracts}")
st.write(f"Total Cost: {total_cost}")
st.write(f"Intrinsic Value per Share: {intrinsic_value_per_share}")
st.write(f"Intrinsic Value per Contract: {intrinsic_value_per_contract}")
st.write(f"Total Intrinsic Value: {total_intrinsic_value}")
st.write(f"Total Profit: {total_profit}")
st.write(f"Profit per Contract: {profit_per_contract}")
