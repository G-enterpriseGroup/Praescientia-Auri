import yfinance as yf
import pandas as pd
import streamlit as st

def calculate_max_loss(stock_price, options_table):
    """
    Calculate Max Loss for each option using both Ask Price and Last Price:
    Max Loss = (Strike Price × 100) - (Cost of Stock + Cost of Put)
    """
    number_of_shares = 100  # Standard contract size

    # Perform calculations using the Ask Price
    options_table['Cost of Put (Ask)'] = options_table['Ask'] * number_of_shares
    options_table['Max Loss (Ask)'] = (
        (options_table['Strike'] * number_of_shares) -
        (stock_price * number_of_shares + options_table['Cost of Put (Ask)'])
    )
    options_table['Max Loss Calc (Ask)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f} × {number_of_shares}) - ({stock_price * number_of_shares:.2f} + {row['Cost of Put (Ask)']:.2f})",
        axis=1
    )

    # Perform calculations using the Last Price
    options_table['Cost of Put (Last)'] = options_table['Last Price'] * number_of_shares
    options_table['Max Loss (Last)'] = (
        (options_table['Strike'] * number_of_shares) -
        (stock_price * number_of_shares + options_table['Cost of Put (Last)'])
    )
    options_table['Max Loss Calc (Last)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f} × {number_of_shares}) - ({stock_price * number_of_shares:.2f} + {row['Cost of Put (Last)']:.2f})",
        axis=1
    )

    return options_table

def display_put_options(ticker_symbol, stock_price):
    try:
        # Fetch Ticker object
        ticker = yf.Ticker(ticker_symbol)
        
        # Fetch available expiration dates
        expiration_dates = ticker.options
        if not expiration_dates:
            st.warning(f"No options data available for ticker {ticker_symbol}.")
            return

        st.write(f"Fetching put options for all available expiration dates of {ticker_symbol}...")

        # DataFrame to consolidate all expiration dates
        all_data = pd.DataFrame()

        # Loop through all expiration dates
        for chosen_date in expiration_dates:
            # Fetch put options for the current expiration date
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                continue
            
            # Prepare put options table
            puts_table = puts[["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]]
            puts_table.columns = ["Contract", "Strike", "Last Price", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility"]
            puts_table["Expiration Date"] = chosen_date

            # Calculate max loss for each option
            puts_table = calculate_max_loss(stock_price, puts_table)

            # Append to the main DataFrame
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

        if all_data.empty:
            st.warning(f"No put options found for {ticker_symbol}.")
            return
        
        # Display the combined data
        st.write(f"Put Options with Max Loss for {ticker_symbol} across all expiration dates:")
        st.dataframe(all_data)
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Streamlit App
st.title("Options Max Loss Calculator")

# User Input
ticker_symbol = st.text_input("Enter the ticker symbol").strip().upper()

if ticker_symbol:
    # Automatically fetch the stock's current price
    ticker = yf.Ticker(ticker_symbol)
    stock_info = ticker.history(period="1d")
    current_price = stock_info["Close"].iloc[-1] if not stock_info.empty else 0.0

    # Display input for the stock price with the default set to the current price
    stock_price = st.number_input(
        "Enter the purchase price per share of the stock",
        min_value=0.0,
        value=float(current_price),
        step=0.01
    )

    if stock_price > 0:
        display_put_options(ticker_symbol, stock_price)
