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

def calculate_covered_call(price, quantity, option_price, strike_price, days_until_expiry):
    initial_premium = option_price * quantity * 100
    max_risk = (price * quantity * 100) - initial_premium
    breakeven = price - option_price
    max_return = ((strike_price - price) * quantity * 100) + initial_premium
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
        
        option_type = st.selectbox("Select Option Type", ["Bid", "Ask"])
        st.write("### Options Chain")
        st.dataframe(chain)
        
        strike_price = st.number_input("Strike Price ($)", value=chain['strike'].iloc[0], step=0.01, format="%.2f")
        quantity = st.number_input("Quantity (shares)", value=100, step=1)
        
        if option_type == "Bid":
            option_price = chain.loc[chain['strike'] == strike_price, 'bid'].values[0]
        else:
            option_price = chain.loc[chain['strike'] == strike_price, 'ask'].values[0]

        days_until_expiry = (pd.to_datetime(selected_expiration_date) - pd.to_datetime('today')).days

        if st.button("Calculate"):
            stock_price = yf.Ticker(ticker).history(period='1d')['Close'][0]
            initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return = calculate_covered_call(
                stock_price, quantity, option_price, strike_price, days_until_expiry)

            st.write("### Results:")
            st.write(f"**Initial Premium Received:** ${initial_premium:.2f}")
            st.write(f"**Maximum Risk:** ${max_risk:.2f}")
            st.write(f"**Break-even Price at Expiry:** ${breakeven:.2f}")
            st.write(f"**Maximum Return:** ${max_return:.2f}")
            st.write(f"**Return on Risk:** {return_on_risk:.2f}%")
            st.write(f"**Annualized Return:** {annualized_return:.2f}%")

            st.write("### Detailed Explanation:")
            st.write("1. **Initial Premium Received:** This is the total premium received from selling the call options.")
            st.write("   - Calculation: Option Price * Quantity * 100")
            st.write(f"   - Example: ${option_price} * {quantity} * 100 = ${initial_premium:.2f}")
            
            st.write("2. **Maximum Risk:** This is the maximum potential loss if the stock price drops to zero.")
            st.write("   - Calculation: (Stock Price * Quantity * 100) - Initial Premium")
            st.write(f"   - Example: (${stock_price} * {quantity} * 100) - ${initial_premium:.2f} = ${max_risk:.2f}")
            
            st.write("3. **Break-even Price at Expiry:** This is the stock price at which the total loss is zero, taking the premium into account.")
            st.write("   - Calculation: Stock Price - Option Price")
            st.write(f"   - Example: ${stock_price} - ${option_price} = ${breakeven:.2f}")
            
            st.write("4. **Maximum Return:** This is the total profit if the stock price is at or above the strike price at expiry.")
            st.write("   - Calculation: ((Strike Price - Stock Price) * Quantity * 100) + Initial Premium")
            st.write(f"   - Example: ((${strike_price} - ${stock_price}) * {quantity} * 100) + ${initial_premium:.2f} = ${max_return:.2f}")
            
            st.write("5. **Return on Risk:** This is the percentage return on the maximum risk taken.")
            st.write("   - Calculation: (Maximum Return / Maximum Risk) * 100")
            st.write(f"   - Example: (${max_return:.2f} / ${max_risk:.2f}) * 100 = {return_on_risk:.2f}%")
            
            st.write("6. **Annualized Return:** This is the annualized percentage return based on the days until expiry.")
            st.write("   - Calculation: (Return on Risk / Days Until Expiry) * 365")
            st.write(f"   - Example: ({return_on_risk:.2f}% / {days_until_expiry}) * 365 = {annualized_return:.2f}%")
