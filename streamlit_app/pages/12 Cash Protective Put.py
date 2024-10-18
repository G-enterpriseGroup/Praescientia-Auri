import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

# Define functions for the put calculator
def get_expiration_dates(ticker):
    stock = yf.Ticker(ticker)
    return stock.options

def get_options_chain(ticker, expiration_date):
    stock = yf.Ticker(ticker)
    options = stock.option_chain(expiration_date)
    options_df = pd.concat([options.calls, options.puts], keys=['Calls', 'Puts'], names=['Type'])
    options_df = options_df.reset_index(level='Type').reset_index(drop=True)
    return options_df

def black_scholes_put(S, K, T, r, sigma):
    if T == 0:
        return max(0, K - S)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    put_price = (K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))
    return put_price

# Streamlit UI for Put Option Calculator
st.title("Put Option Calculator (Options Profit Calculator Style)")

ticker = st.text_input("Ticker Symbol", value="AAPL")
if ticker:
    expiration_dates = get_expiration_dates(ticker)
    selected_expiration_date = st.selectbox("Select Expiration Date", expiration_dates)
    
    if selected_expiration_date:
        chain = get_options_chain(ticker, selected_expiration_date)
        
        strike_prices = chain['strike'].unique()
        
        stock_price = yf.Ticker(ticker).history(period='1d')['Close'][0]
        closest_strike_price = min(strike_prices, key=lambda x: abs(x - stock_price))
        
        selected_strike_price = st.selectbox("Select Strike Price", strike_prices, index=list(strike_prices).index(closest_strike_price))
        
        if selected_strike_price:
            selected_option = chain[chain['strike'] == selected_strike_price]
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
                # Calculate P&L at expiration (long put)
                initial_premium = option_price * quantity * 100
                breakeven = selected_strike_price - option_price
                max_risk = initial_premium
                max_return = (selected_strike_price - stock_price) * quantity * 100 - initial_premium if stock_price < selected_strike_price else -initial_premium
                profit_at_expiry = np.maximum(selected_strike_price - stock_price, 0) * 100 * quantity - initial_premium
                
                # Greeks calculation (assuming a constant IV and risk-free rate)
                r = 0.01  # Risk-free rate
                iv = selected_option['impliedVolatility'].values[0]  # Implied Volatility
                T = days_until_expiry / 365.0  # Time to expiration in years

                delta, gamma, theta, vega, rho = calculate_greeks(stock_price, selected_strike_price, T, r, iv, 'put')

                st.write("### Results:")
                st.write(f"**Initial Premium Paid:** ${initial_premium:.2f}")
                st.write(f"**Break-even Price at Expiry:** ${breakeven:.2f}")
                st.write(f"**Maximum Return at Expiry:** ${max_return:.2f}")
                st.write(f"**Profit at Expiry:** ${profit_at_expiry:.2f}")

                st.write("### Option Greeks:")
                st.write(f"**Implied Volatility:** {iv * 100:.2f}")
                st.write(f"**Delta:** {delta:.2f}")
                st.write(f"**Gamma:** {gamma:.2f}")
                st.write(f"**Theta (per day):** {theta:.2f}")
                st.write(f"**Vega:** {vega:.2f}")
                st.write(f"**Rho:** {rho:.2f}")

# Create price range with increments of 0.50
initial_stock_price = stock_price
strike_price = selected_strike_price
days_to_expiration = days_until_expiry
risk_free_rate = 0.01
initial_premium_paid = option_price
price_range = np.round(np.arange(initial_stock_price - 13 * 0.50, initial_stock_price + 14 * 0.50, 0.50), 2)
iv = selected_option['impliedVolatility'].values[0]

# Create a DataFrame to store results
columns = ['Price'] + [f'Day_{day}' for day in range(1, days_to_expiration + 1)]
results = pd.DataFrame(columns=columns)

# Calculate P&L for each stock price and each day
for price in price_range:
    row = [price]
    for day in range(1, days_to_expiration + 1):
        T = (days_to_expiration - day) / 365
        put_price = black_scholes_put(price, strike_price, T, risk_free_rate, iv)
        long_put_value = max(0, strike_price - price) * 100 * quantity - (
