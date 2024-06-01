import streamlit as st

# Function to calculate covered call metrics
def calculate_covered_call(price, quantity, option_price, strike_price, days_until_expiry):
    initial_premium = option_price * quantity * 100
    max_risk = (price * quantity) - initial_premium
    breakeven = price - option_price
    max_return = ((strike_price - price) * quantity * 100) + initial_premium
    return_on_risk = max_return / max_risk * 100
    annualized_return = (return_on_risk / days_until_expiry) * 365
    return initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return

# Streamlit app
st.title("Covered Call Calculator")

price = st.number_input("Stock Price", value=49.75, step=0.01)
quantity = st.number_input("Quantity", value=100, step=1)
option_price = st.number_input("Option Price", value=1.35, step=0.01)
strike_price = st.number_input("Strike Price", value=50.00, step=0.01)
days_until_expiry = st.number_input("Days Until Expiry", value=20, step=1)

if st.button("Calculate"):
    initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return = calculate_covered_call(price, quantity, option_price, strike_price, days_until_expiry)
    
    st.write(f"Initial Premium: ${initial_premium:.2f}")
    st.write(f"Max Risk: ${max_risk:.2f}")
    st.write(f"Break-even at Expiry: ${breakeven:.2f}")
    st.write(f"Max Return: ${max_return:.2f}")
    st.write(f"Return on Risk: {return_on_risk:.2f}%")
    st.write(f"Annualized Return: {annualized_return:.2f}%")

# Run the Streamlit app with `streamlit run covered_call_calculator.py`
