import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm

st.set_page_config(layout="wide")

# Define functions for the put calculator
def get_expiration_dates(ticker):
    stock = yf.Ticker(ticker)
    return stock.options

def get_options_chain(ticker, expiration_date):
    stock = yf.Ticker(ticker)
    options = stock.option_chain(expiration_date)
    return options.puts

def calculate_greeks(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    delta = -norm.cdf(-d1)
    theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
    return delta, gamma, theta, vega, rho

# Streamlit UI for Put Calculator
st.title("Put Option Calculator")

ticker = st.text_input("Ticker Symbol", value="AAPL")
if ticker:
    expiration_dates = get_expiration_dates(ticker)
    selected_expiration_date = st.selectbox("Select Expiration Date", expiration_dates)

    if selected_expiration_date:
        puts = get_options_chain(ticker, selected_expiration_date)

        strike_prices = puts['strike'].unique()
        stock_price = yf.Ticker(ticker).history(period='1d')['Close'][0]
        closest_strike_price = min(strike_prices, key=lambda x: abs(x - stock_price))
        
        selected_strike_price = st.selectbox("Select Strike Price", strike_prices, index=list(strike_prices).index(closest_strike_price))
        
        if selected_strike_price:
            selected_option = puts[puts['strike'] == selected_strike_price]
            bid_price = selected_option['bid'].values[0]
            ask_price = selected_option['ask'].values[0]
            
            bid_price = st.text_input("Bid Price", value=f"{bid_price:.2f}")
            ask_price = st.text_input("Ask Price", value=f"{ask_price:.2f}")

            option_type = st.radio("Select Option Type", ["Bid", "Ask"])
            if option_type == "Bid":
                option_price = float(bid_price)
            else:
                option_price = float(ask_price)

            quantity = st.number_input("Quantity (shares)", value=100, step=1)
            days_until_expiry = (pd.to_datetime(selected_expiration_date) - pd.to_datetime('today')).days

            if st.button("Calculate"):
                r = 0.01  # Risk-free rate
                iv = selected_option['impliedVolatility'].values[0]
                T = days_until_expiry / 365.0

                delta, gamma, theta, vega, rho = calculate_greeks(stock_price, selected_strike_price, T, r, iv)

                max_profit = (selected_strike_price - 0) * quantity * 100 - (option_price * quantity * 100)
                max_loss = option_price * quantity * 100  # Premium paid
                breakeven = selected_strike_price - option_price

                st.write("### Results:")
                st.write(f"**Initial Premium Paid:** ${max_loss:.2f}")
                st.write(f"**Maximum Profit:** ${max_profit:.2f}")
                st.write(f"**Break-even Price at Expiry:** ${breakeven:.2f}")
                st.write("### Option Greeks:")
                st.write(f"**Implied Volatility:** {iv * 100:.2f}")
                st.write(f"**Delta:** {delta:.2f}")
                st.write(f"**Gamma:** {gamma:.2f}")
                st.write(f"**Theta (per day):** {theta:.2f}")
                st.write(f"**Vega:** {vega:.2f}")
                st.write(f"**Rho:** {rho:.2f}")

