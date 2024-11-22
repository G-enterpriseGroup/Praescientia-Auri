import streamlit as st
import yfinance as yf
from datetime import datetime

# Page Title
st.title("Protective Put (Married Put) Max Loss Calculator")

# Step 1: Ticker Input
ticker = st.text_input("Enter the stock ticker:", "")

if ticker:
    # Fetch ticker data
    try:
        stock = yf.Ticker(ticker)
        options = stock.options
    except Exception as e:
        st.error("Error fetching ticker data. Please check the ticker.")
        st.stop()

    # Step 2: Expiration Selection
    if options:
        expiration = st.selectbox("Select an expiration date:", options)
    else:
        st.error("No options available for this ticker.")
        st.stop()

    # Step 3: Fetch Put Options Chain
    if expiration:
        try:
            option_chain = stock.option_chain(expiration)
            puts = option_chain.puts
        except Exception as e:
            st.error("Error fetching options data.")
            st.stop()

        # Display put options table
        st.write("Put Options Chain:")
        st.dataframe(puts[["strike", "lastPrice", "bid", "ask"]])

        # Step 4: Strike Price Selection
        selected_strike = st.selectbox("Select a strike price:", puts["strike"])

        # Get the premium for the selected strike
        premium_row = puts[puts["strike"] == selected_strike]
        premium = (premium_row["bid"].values[0] + premium_row["ask"].values[0]) / 2

        st.write(f"Premium for selected put option: ${premium:.2f}")

    # Step 5: Input Stock Holdings and Acquisition Prices
    st.write("Input your stock holdings:")
    holdings = st.text_area(
        "Enter the stock ticker and acquisition price (one per line, format: TICKER,PRICE):"
    )

    # Parse holdings input
    if holdings:
        holdings_data = []
        for line in holdings.split("\n"):
            try:
                ticker, price = line.split(",")
                holdings_data.append((ticker.strip().upper(), float(price.strip())))
            except ValueError:
                st.error(f"Invalid line format: {line}. Use TICKER,PRICE format.")
                st.stop()

        # Display holdings
        st.write("Your stock holdings:")
        for h_ticker, h_price in holdings_data:
            st.write(f"Ticker: {h_ticker}, Acquisition Price: ${h_price:.2f}")

        # Step 6: Calculate Max Loss for Protective Put
        if st.button("Calculate Max Loss"):
            for h_ticker, h_price in holdings_data:
                if h_ticker == ticker.upper():
                    cost_basis = h_price + premium
                    max_loss = cost_basis - selected_strike

                    st.write(
                        f"For {h_ticker}, with acquisition price ${h_price:.2f},"
                        f" strike price ${selected_strike:.2f}, and premium ${premium:.2f}:"
                    )
                    st.write(f"Cost Basis: ${cost_basis:.2f}")
                    st.write(f"Max Loss: ${max_loss:.2f}")
                    break
            else:
                st.error("Ticker in holdings does not match the selected ticker.")
