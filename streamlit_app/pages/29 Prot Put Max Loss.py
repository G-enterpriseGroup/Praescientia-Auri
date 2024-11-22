import streamlit as st
import yfinance as yf

# Streamlit App Title
st.title("Protective Put Max Loss Calculator")

# User Inputs
ticker = st.text_input("Enter the Stock Ticker (e.g., AAPL):", value="AAPL")
stock_price = st.number_input("Enter the Stock Purchase Price:", min_value=0.0, value=32.20, step=0.01)
shares = st.number_input("Enter the Number of Shares You Own:", min_value=1, value=100, step=1)
strike_price = st.number_input("Enter the Put Strike Price:", min_value=0.0, value=40.0, step=0.01)
premium = st.number_input("Enter the Premium (Put Ask Price):", min_value=0.0, value=8.70, step=0.01)

# Calculate Max Loss
if st.button("Calculate Max Loss"):
    # Cost of Stock
    stock_cost = stock_price * shares
    
    # Cost of Put
    put_cost = premium * shares
    
    # Total Maximum Loss
    max_loss = (stock_cost + put_cost) - (strike_price * shares)
    
    # Display Results
    st.subheader("Calculation Results:")
    st.write(f"**Stock Cost:** ${stock_cost:.2f}")
    st.write(f"**Put Cost:** ${put_cost:.2f}")
    st.write(f"**Maximum Loss:** ${max_loss:.2f}")
    st.write(f"This is your maximum possible loss if the stock price drops significantly.")

# Additional Information
st.info("Note: The calculations are based on 100 shares per option contract. Adjust values if necessary.")
