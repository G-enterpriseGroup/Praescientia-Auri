You said:
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Set Streamlit page configuration
st.set_page_config(page_title="Married Put", layout="wide")

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

def calculate_trading_days_left(expiration_date):
    """
    Calculate the total number of days left until the expiration date.
    """
    today = datetime.today()
    expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
    return (expiration_date - today).days

def display_put_options_all_dates(ticker_symbol, stock_price):
    try:
        ticker = yf.Ticker(ticker_symbol)
        expiration_dates = ticker.options
        if not expiration_dates:
            st.error(f"No options data available for ticker {ticker_symbol}.")
            return

        all_data = pd.DataFrame()

        for chosen_date in expiration_dates:
            trading_days_left = calculate_trading_days_left(chosen_date)
            st.subheader(f"Expiration Date: {chosen_date} ({trading_days_left} trading days left)")

            # Fetch put options
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                st.warning(f"No puts available for expiration date {chosen_date}.")
                continue

            # Prepare full put options table (for calculations)
            puts_table = puts[["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]]
            puts_table.columns = ["Contract", "Strike", "Last Price", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility"]
            puts_table["Expiration Date"] = chosen_date

            # Run max loss calculation
            puts_table = calculate_max_loss(stock_price, puts_table)

            # Create a "display" version that hides unwanted columns
            display_table = puts_table.drop(
                columns=["Last Price", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility", "Expiration Date"]
            )

            # Append to full dataset (keep all for CSV)
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # Highlight only the Max Loss columns
            styled_table = display_table.style.highlight_max(
                subset=["Max Loss (Ask)", "Max Loss (Last)"], color="yellow"
            )
            st.dataframe(styled_table)

        if not all_data.empty:
            # Download button still includes everything
            csv = all_data.to_csv(index=False)
            st.download_button(
                label="Download All Expiration Data as CSV",
                data=csv,
                file_name=f"{ticker_symbol}_put_options.csv",
                mime="text/csv",
            )
        else:
            st.warning(f"No put options data to display or download for {ticker_symbol}.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

def main():
    st.title("Options Analysis with Max Loss Calculation")

    ticker_symbol = st.text_input("Enter the ticker symbol:", "").upper().strip()

    if ticker_symbol:
        try:
            ticker = yf.Ticker(ticker_symbol)
            long_name = ticker.info.get("longName", "N/A")
            st.write(f"**Company Name:** {long_name}")
        except Exception as e:
            st.warning(f"Unable to fetch company name: {e}")

    if not ticker_symbol:
        st.warning("Please enter a valid ticker symbol.")
        return

    try:
        ticker = yf.Ticker(ticker_symbol)
        stock_info = ticker.history(period="1d")
        current_price = stock_info["Close"].iloc[-1] if not stock_info.empty else 0.0
    except Exception:
        current_price = 0.0

    stock_price = st.number_input(
        "Enter the purchase price per share of the stock:",
        min_value=0.0,
        value=float(current_price),
        step=0.01
    )
    if stock_price <= 0:
        st.warning("Please enter a valid stock price.")
        return

    if st.button("Fetch Options Data"):
        display_put_options_all_dates(ticker_symbol, stock_price)

if __name__ == "__main__":
    main()
