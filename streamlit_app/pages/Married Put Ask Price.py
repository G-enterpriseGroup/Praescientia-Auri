import streamlit as st
import yfinance as yf
import pandas as pd


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


def display_put_options_all_dates(ticker_symbol, stock_price):
    try:
        # Fetch Ticker object
        ticker = yf.Ticker(ticker_symbol)
        
        # Fetch available expiration dates
        expiration_dates = ticker.options
        if not expiration_dates:
            st.error(f"No options data available for ticker {ticker_symbol}.")
            return

        for chosen_date in expiration_dates:
            st.subheader(f"Expiration Date: {chosen_date}")
            
            # Fetch put options for the current expiration date
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                st.warning(f"No puts available for expiration date {chosen_date}.")
                continue
            
            # Prepare put options table
            puts_table = puts[["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]]
            puts_table.columns = ["Contract", "Strike", "Last Price", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility"]
            
            # Calculate max loss for each option
            puts_table = calculate_max_loss(stock_price, puts_table)
            
            # Display the table
            st.dataframe(puts_table)

    except Exception as e:
        st.error(f"An error occurred: {e}")


def main():
    st.title("Options Analysis with Max Loss Calculation")

    # Input for ticker symbol
    ticker_symbol = st.text_input("Enter the ticker symbol:", "").upper().strip()
    if not ticker_symbol:
        st.warning("Please enter a valid ticker symbol.")
        return

    # Automatically fetch the current stock price
    try:
        ticker = yf.Ticker(ticker_symbol)
        stock_info = ticker.history(period="1d")
        current_price = stock_info["Close"].iloc[-1] if not stock_info.empty else 0.0
    except Exception:
        current_price = 0.0

    # Input for purchase price per share with default value
    stock_price = st.number_input(
        "Enter the purchase price per share of the stock:",
        min_value=0.0,
        value=float(current_price),
        step=0.01
    )
    if stock_price <= 0:
        st.warning("Please enter a valid stock price.")
        return

    # Fetch and display options data
    if st.button("Fetch Options Data"):
        display_put_options_all_dates(ticker_symbol, stock_price)


if __name__ == "__main__":
    main()
