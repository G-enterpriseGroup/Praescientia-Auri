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

# Build a copy-button table aligned with contracts
def build_copy_table(contracts):
    copy_table = pd.DataFrame({
        "Copy": [
            f"""<button onclick="navigator.clipboard.writeText('{c}')">Copy</button>"""
            for c in contracts
        ]
    })
    return copy_table

def display_put_options_all_dates(ticker_symbol, stock_price):
    try:
        # Fetch Ticker object
        ticker = yf.Ticker(ticker_symbol)

        # Fetch available expiration dates
        expiration_dates = ticker.options
        if not expiration_dates:
            st.error(f"No options data available for ticker {ticker_symbol}.")
            return

        all_data = pd.DataFrame()

        for chosen_date in expiration_dates:
            trading_days_left = calculate_trading_days_left(chosen_date)
            st.subheader(f"Expiration Date: {chosen_date} ({trading_days_left} trading days left)")

            # Fetch put options for the current expiration date
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                st.warning(f"No puts available for expiration date {chosen_date}.")
                continue

            # Prepare put options table
            puts_table = puts[["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]]
            puts_table.columns = ["Contract", "Strike", "Last Price", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility"]
            puts_table["Expiration Date"] = chosen_date

            # Calculate max loss for each option
            puts_table = calculate_max_loss(stock_price, puts_table)

            # Build copy button table aligned with contracts
            copy_table = build_copy_table(puts_table["Contract"])

            # Display side by side
            col1, col2 = st.columns([5,1])
            with col1:
                st.dataframe(puts_table, use_container_width=True)
            with col2:
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.write(copy_table.to_html(escape=False, index=False), unsafe_allow_html=True)

            all_data = pd.concat([all_data, puts_table], ignore_index=True)

        return all_data

    except Exception as e:
        st.error(f"Error fetching data for {ticker_symbol}: {e}")
        return pd.DataFrame()

def main():
    st.title("Married Put Strategy Calculator")

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
