import streamlit as st
import yfinance as yf
import pandas as pd

# Page Title
st.set_page_config(page_title="Protective Put Calculator", layout="wide")
st.title("Dynamic Protective Put (Married Put) Calculator")

# Step 1: Ticker Input
ticker = st.text_input("Enter the stock ticker:", "").strip().upper()

if ticker:
    try:
        # Fetch ticker data
        stock = yf.Ticker(ticker)
        expiration_dates = stock.options
    except Exception as e:
        st.error("Error fetching ticker data. Please check the ticker.")
        st.stop()

    if expiration_dates:
        # Step 2: Expiration Selection
        st.subheader("Step 2: Choose Expiration Date")
        expiration = st.selectbox("Select an expiration date:", expiration_dates)

        if expiration:
            try:
                # Fetch option chain for the selected expiration
                option_chain = stock.option_chain(expiration)
                puts = option_chain.puts
            except Exception as e:
                st.error("Error fetching options chain data.")
                st.stop()

            # Step 3: Display Strike Prices
            st.subheader("Step 3: Select Strike Price")
            st.write("Available Put Options:")
            st.dataframe(
                puts[["strike", "lastPrice", "bid", "ask"]].style.set_table_styles(
                    [{"selector": "table", "props": [("width", "100%")]}]
                )
            )
            strike_prices = puts["strike"].tolist()
            selected_strike = st.selectbox("Choose a strike price:", strike_prices)

            # Calculate the premium for the selected strike price
            premium_row = puts[puts["strike"] == selected_strike]
            if not premium_row.empty:
                premium = (premium_row["bid"].values[0] + premium_row["ask"].values[0]) / 2
                st.write(f"Premium for the selected put option: **${premium:.2f}**")
            else:
                st.error("Error fetching premium for the selected strike price.")
                st.stop()

            # Step 4: Input Stock Holdings
            st.subheader("Step 4: Input Stock Holdings")
            holdings_input = st.text_area(
                "Enter stock ticker and acquisition price (format: TICKER,PRICE, one per line):"
            )

            if holdings_input:
                # Parse holdings input
                holdings_data = []
                for line in holdings_input.split("\n"):
                    try:
                        h_ticker, h_price = line.split(",")
                        holdings_data.append((h_ticker.strip().upper(), float(h_price.strip())))
                    except ValueError:
                        st.error(f"Invalid format in line: {line}. Use TICKER,PRICE.")
                        st.stop()

                # Display holdings in a wide table
                holdings_df = pd.DataFrame(holdings_data, columns=["Ticker", "Acquisition Price"])
                st.write("Your Stock Holdings:")
                st.dataframe(holdings_df.style.set_table_styles(
                    [{"selector": "table", "props": [("width", "100%")]}]
                ))

                # Step 5: Calculate Max Loss
                st.subheader("Step 5: Calculate Max Loss")
                if st.button("Calculate Max Loss"):
                    results = []
                    for h_ticker, h_price in holdings_data:
                        if h_ticker == ticker:
                            cost_basis = h_price + premium
                            max_loss = max(cost_basis - selected_strike, 0)
                            results.append(
                                {
                                    "Ticker": h_ticker,
                                    "Acquisition Price": h_price,
                                    "Strike Price": selected_strike,
                                    "Premium": premium,
                                    "Cost Basis": cost_basis,
                                    "Max Loss": max_loss,
                                }
                            )
                        else:
                            st.warning(
                                f"Ticker {h_ticker} does not match the selected ticker ({ticker}). Skipping."
                            )

                    if results:
                        results_df = pd.DataFrame(results)
                        st.write("Calculation Results:")
                        st.dataframe(results_df.style.set_table_styles(
                            [{"selector": "table", "props": [("width", "100%")]}]
                        ))
                    else:
                        st.warning("No matching tickers found for calculations.")
