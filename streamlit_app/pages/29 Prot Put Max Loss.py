import streamlit as st
import yfinance as yf
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Protective Put Max Loss Calculator", layout="wide")

# Title
st.title("Protective Put (Married Put) Max Loss Calculator")

# Step 1: Enter Ticker
ticker = st.text_input("Enter the stock ticker:", "").strip().upper()

if ticker:
    try:
        stock = yf.Ticker(ticker)
        expiration_dates = stock.options
    except Exception as e:
        st.error("Error fetching data. Please verify the ticker.")
        st.stop()

    if expiration_dates:
        # Step 2: Select Expiration Date
        st.subheader("Step 2: Choose Expiration Date")
        expiration = st.selectbox("Select an expiration date:", expiration_dates)

        if expiration:
            try:
                # Fetch option chain
                option_chain = stock.option_chain(expiration)
                puts = option_chain.puts
            except Exception as e:
                st.error("Error fetching options chain data.")
                st.stop()

            # Display Put Options Chain
            st.subheader("Step 3: Select Strike Price")
            st.write("Available Put Options:")
            st.dataframe(
                puts[["strike", "lastPrice", "bid", "ask"]].style.set_table_styles(
                    [{"selector": "table", "props": [("width", "100%")]}]
                )
            )

            # Strike Price Selection
            selected_strike = st.selectbox("Choose a strike price:", puts["strike"])

            # Calculate Premium
            premium_row = puts[puts["strike"] == selected_strike]
            if not premium_row.empty:
                premium = (premium_row["bid"].values[0] + premium_row["ask"].values[0]) / 2
                st.write(f"Premium for selected put option: **${premium:.2f}**")
            else:
                st.error("Error fetching premium data.")
                st.stop()

            # Step 4: Enter Stock Holdings
            st.subheader("Step 4: Input Stock Holdings")
            acquisition_price = st.number_input(
                "Enter the acquisition price of the stock:", min_value=0.0, format="%.2f"
            )
            stock_quantity = st.number_input(
                "Enter the number of shares:", min_value=1, step=1
            )

            # Step 5: Calculate Max Loss
            if st.button("Calculate Max Loss"):
                cost_basis_per_share = acquisition_price + premium
                total_cost_basis = cost_basis_per_share * stock_quantity
                max_loss_per_share = max(cost_basis_per_share - selected_strike, 0)
                total_max_loss = max_loss_per_share * stock_quantity

                st.subheader("Calculation Results")
                st.write(f"**Cost Basis per Share:** ${cost_basis_per_share:.2f}")
                st.write(f"**Max Loss per Share:** ${max_loss_per_share:.2f}")
                st.write(f"**Total Cost Basis:** ${total_cost_basis:.2f}")
                st.write(f"**Total Max Loss:** ${total_max_loss:.2f}")
