import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
st.set_page_config(layout="wide")
# Define functions for the covered call calculator
def get_expiration_dates(ticker):
    stock = yf.Ticker(ticker)
    return stock.options

def get_options_chain(ticker, expiration_date):
    stock = yf.Ticker(ticker)
    options = stock.option_chain(expiration_date)
    options_df = pd.concat([options.calls, options.puts], keys=['Calls', 'Puts'], names=['Type'])
    options_df = options_df.reset_index(level='Type').reset_index(drop=True)
    return options_df

def calculate_greeks(S, K, T, r, sigma, option_type="call"):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        delta = norm.cdf(d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        delta = -norm.cdf(-d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365

    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    rho = K * T * np.exp(-r * T) * norm.cdf(d2) if option_type == "call" else -K * T * np.exp(-r * T) * norm.cdf(-d2)

    return delta, gamma, theta, vega, rho

def calculate_covered_call(price, quantity, option_price, strike_price, days_until_expiry):
    initial_premium = option_price * quantity
    max_risk = (price * quantity) - initial_premium
    breakeven = price - option_price
    max_return = ((strike_price - price) * quantity) + initial_premium
    return_on_risk = (max_return / max_risk) * 100
    annualized_return = ((return_on_risk / days_until_expiry) * 365)
    return initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return

# Streamlit UI for Covered Call Calculator
st.title("Covered Call Calculator")

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
                initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return = calculate_covered_call(
                    stock_price, quantity, option_price, selected_strike_price, days_until_expiry)

                r = 0.01  # Risk-free rate
                iv = selected_option['impliedVolatility'].values[0]  # Implied Volatility
                T = days_until_expiry / 365.0  # Time to expiration in years

                delta, gamma, theta, vega, rho = calculate_greeks(stock_price, selected_strike_price, T, r, iv, 'call')

                st.write("### Results:")
                st.write(f"**Initial Premium Received:** ${initial_premium:.2f}")
                st.write(f"**Maximum Risk:** ${max_risk:.2f}")
                st.write(f"**Break-even Price at Expiry:** ${breakeven:.2f}")
                st.write(f"**Maximum Return:** ${max_return:.2f}")
                st.write(f"**Return on Risk:** {return_on_risk:.2f}%")
                st.write(f"**Annualized Return:** {annualized_return:.2f}%")
                st.write("### Option Greeks:")
                st.write(f"**Implied Volatility:** {iv * 100:.2f}")
                st.write(f"**Delta:** {delta:.2f}")
                st.write(f"**Gamma:** {gamma:.2f}")
                st.write(f"**Theta (per day):** {theta:.2f}")
                st.write(f"**Vega:** {vega:.2f}")
                st.write(f"**Rho:** {rho:.2f}")

# Black-Scholes formula for a call option
def black_scholes_call(S, K, T, r, sigma):
    if T == 0:
        return max(0, S - K)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call_price = (S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    return call_price

# Create price range with increments of 0.75
initial_stock_price = stock_price  # Example value, replace with actual input
strike_price = selected_strike_price         # Example value, replace with actual input
days_to_expiration = days_until_expiry    # Example value, replace with actual input
risk_free_rate = 0.01      # Example value, replace with actual input
initial_premium_received = option_price  # Example value, replace with actual input
price_range = np.round(np.arange(initial_stock_price - 13 * 0.75, initial_stock_price + 14 * 0.75, 0.75), 2)
iv = selected_option['impliedVolatility'].values[0]  # Implied Volatility

# Create a DataFrame to store results
columns = ['Price'] + [f'Day_{day}' for day in range(1, days_to_expiration + 1)]
results = pd.DataFrame(columns=columns)

# Calculate P&L for each stock price and each day
for price in price_range:
    row = [price]
    for day in range(1, days_to_expiration + 1):
        # Time to expiration in years
        T = (days_to_expiration - day) / 365
        # Calculate the option price using Black-Scholes model
        call_price = black_scholes_call(price, strike_price, T, risk_free_rate, iv)
        # Calculate the value of the covered call position
        covered_call_value = (price - initial_stock_price) * 100 - (call_price * 100) + initial_premium_received * 100
        row.append(covered_call_value)
    results.loc[len(results)] = row

# Apply conditional formatting
def color_negative_red_positive_green(val):
    if val > 0:
        color = f'rgb({255 - int((val / results.max().max()) * 255)}, 255, {255 - int((val / results.max().max()) * 255)})'
    else:
        color = f'rgb(255, {255 - int((abs(val) / abs(results.min().min())) * 255)}, {255 - int((abs(val) / abs(results.min().min())) * 255)})'
    return f'background-color: {color}; color: black;'

# Apply the formatting to the DataFrame
formatted_results = results.style.applymap(color_negative_red_positive_green, subset=columns[1:])
st.dataframe(formatted_results, use_container_width=True)
st.write("### Profit and Loss Table:")
st.dataframe(formatted_results)
