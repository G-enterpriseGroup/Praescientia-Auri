if selected_strike_price:
    selected_option = chain[chain['strike'] == selected_strike_price]
    if not selected_option.empty:
        bid_price = selected_option['bid'].values[0]
        ask_price = selected_option['ask'].values[0]

        st.write(f"Bid Price: ${bid_price:.2f}")
        st.write(f"Ask Price: ${ask_price:.2f}")

        option_type = st.radio("Select Option Type", ["Bid", "Ask"])
        if option_type == "Bid":
            option_price = bid_price
        else:
            option_price = ask_price

        quantity = st.number_input("Quantity (shares)", value=100, step=1)
        days_until_expiry = (pd.to_datetime(selected_expiration_date) - pd.to_datetime('today')).days

        if st.button("Calculate"):
            initial_premium, max_risk, breakeven, max_return, return_on_risk, annualized_return = calculate_covered_call(
                stock_price, quantity, option_price, selected_strike_price, days_until_expiry)

            r = 0.01  # Risk-free rate (you can adjust this as necessary)
            iv = selected_option['impliedVolatility'].values[0]  # Implied Volatility as a decimal            
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
            st.write(f"**Implied Volatility:** {iv:.2f}")
            st.write(f"**Delta:** {delta:.2f}")
            st.write(f"**Gamma:** {gamma:.2f}")
            st.write(f"**Theta (per day):** {theta:.2f}")
            st.write(f"**Vega:** {vega:.2f}")
            st.write(f"**Rho:** {rho:.2f}")
