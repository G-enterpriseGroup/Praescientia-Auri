import streamlit as st

# Function to calculate covered call metrics
def calculate_covered_call(price, quantity, option_price, strike_price, days_until_expiry):
    initial_premium = option_price * quantity * 100
    max_risk = (price * quantity * 100) - initial_premium
    breakeven = price - option_price
    max_return = ((strike_price - price) * quantity * 100) + initial_premium
    return_on_risk = (max_return / max_risk) * 100
    annualized_return = ((return_on_risk / days_until_expiry) * 365)
    return initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return

# Streamlit app
st.title("Covered Call Calculator")

st.write("Enter the details for the covered call option:")

price = st.number_input("Stock Price ($)", value=49.75, step=0.01, format="%.2f")
quantity = st.number_input("Quantity (shares)", value=100, step=1)
option_price = st.number_input("Option Price ($)", value=1.35, step=0.01, format="%.2f")
strike_price = st.number_input("Strike Price ($)", value=50.00, step=0.01, format="%.2f")
days_until_expiry = st.number_input("Days Until Expiry", value=20, step=1)

if st.button("Calculate"):
    initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return = calculate_covered_call(price, quantity, option_price, strike_price, days_until_expiry)

    st.write("### Results:")
    st.write(f"**Initial Premium Received:** ${initial_premium:.2f}")
    st.write(f"**Maximum Risk:** ${max_risk:.2f}")
    st.write(f"**Break-even Price at Expiry:** ${breakeven:.2f}")
    st.write(f"**Maximum Return:** ${max_return:.2f}")
    st.write(f"**Return on Risk:** {return_on_risk:.2f}%")
    st.write(f"**Annualized Return:** {annualized_return:.2f}%")
    
    # Detailed Explanation
    st.write("### Detailed Explanation:")
    st.write("1. **Initial Premium Received:** This is the total premium received from selling the call options.")
    st.write("   - Calculation: Option Price * Quantity * 100")
    st.write(f"   - Example: ${option_price} * {quantity} * 100 = ${initial_premium:.2f}")
    
    st.write("2. **Maximum Risk:** This is the maximum potential loss if the stock price drops to zero.")
    st.write("   - Calculation: (Stock Price * Quantity * 100) - Initial Premium")
    st.write(f"   - Example: (${price} * {quantity} * 100) - ${initial_premium:.2f} = ${max_risk:.2f}")
    
    st.write("3. **Break-even Price at Expiry:** This is the stock price at which the total loss is zero, taking the premium into account.")
    st.write("   - Calculation: Stock Price - Option Price")
    st.write(f"   - Example: ${price} - ${option_price} = ${breakeven:.2f}")
    
    st.write("4. **Maximum Return:** This is the total profit if the stock price is at or above the strike price at expiry.")
    st.write("   - Calculation: ((Strike Price - Stock Price) * Quantity * 100) + Initial Premium")
    st.write(f"   - Example: ((${strike_price} - ${price}) * {quantity} * 100) + ${initial_premium:.2f} = ${max_return:.2f}")
    
    st.write("5. **Return on Risk:** This is the percentage return on the maximum risk taken.")
    st.write("   - Calculation: (Maximum Return / Maximum Risk) * 100")
    st.write(f"   - Example: (${max_return:.2f} / ${max_risk:.2f}) * 100 = {return_on_risk:.2f}%")
    
    st.write("6. **Annualized Return:** This is the annualized percentage return based on the days until expiry.")
    st.write("   - Calculation: (Return on Risk / Days Until Expiry) * 365")
    st.write(f"   - Example: ({return_on_risk:.2f}% / {days_until_expiry}) * 365 = {annualized_return:.2f}%")

# Run the Streamlit app with `streamlit run covered_call_calculator.py`

