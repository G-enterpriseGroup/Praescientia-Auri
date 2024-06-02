import streamlit as st
import yfinance as yf
import pandas as pd

def get_expiration_dates(ticker):
    stock = yf.Ticker(ticker)
    return stock.options

def get_options_chain(ticker, expiration_date):
    stock = yf.Ticker(ticker)
    options = stock.option_chain(expiration_date)
    options_df = pd.concat([options.calls, options.puts], keys=['Calls', 'Puts'], names=['Type'])
    options_df = options_df.reset_index(level='Type').reset_index(drop=True)
    return options_df

def get_option_greeks(ticker, expiration_date, strike_price, option_type):
    stock = yf.Ticker(ticker)
    option = stock.option_chain(expiration_date)
    if option_type == 'Call':
        option_data = option.calls
    else:
        option_data = option.puts

    selected_option = option_data[option_data['strike'] == strike_price].iloc[0]
    return selected_option['impliedVolatility'], selected_option['delta'], selected_option['gamma'], selected_option['theta'], selected_option['vega'], selected_option['rho']

def calculate_covered_call(price, quantity, option_price, strike_price, days_until_expiry):
    initial_premium = option_price * quantity
    max_risk = (price * quantity) - initial_premium
    breakeven = price - option_price
    max_return = ((strike_price - price) * quantity) + initial_premium
    return_on_risk = (max_return / max_risk) * 100
    annualized_return = ((return_on_risk / days_until_expiry) * 365)
    return initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return

st.title("Covered Call Calculator")

ticker = st.text_input("Ticker Symbol", value="AAPL")
if ticker:
    expiration_dates = get_expiration_dates(ticker)
    selected_expiration_date = st.selectbox("Select Expiration Date", expiration_dates)
    
    if selected_expiration_date:
        chain = get_options_chain(ticker, selected_expiration_date)
        
        strike_prices = chain['strike'].unique()
        
        stock_price = yf.Ticker(ticker).history(period='1d')['Close'][0]
        stock_price
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

                iv, delta, gamma, theta, vega, rho = get_option_greeks(ticker, selected_expiration_date, selected_strike_price, 'Call')

                st.write("### Results:")
                st.write(f"**Initial Premium Received:** ${initial_premium:.2f}")
                st.write(f"**Maximum Risk:** ${max_risk:.2f}")
                st.write(f"**Break-even Price at Expiry:** ${breakeven:.2f}")
                st.write(f"**Maximum Return:** ${max_return:.2f}")
                st.write(f"**Return on Risk:** {return_on_risk:.2f}%")
                st.write(f"**Annualized Return:** {annualized_return:.2f}%")
                st.write("### Option Greeks:")
                st.write(f"**Implied Volatility:** {iv:.2f}")
                st.write(f"**Delta:** {delta:.2f}")
                st.write(f"**Gamma:** {gamma:.2f}")
                st.write(f"**Theta:** {theta:.2f}")
                st.write(f"**Vega:** {vega:.2f}")
                st.write(f"**Rho:** {rho:.2f}")
