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

def fetch_put_options(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    expiration_dates = ticker.options
    options_data = {}

    for exp in expiration_dates:
        opt = ticker.option_chain(exp)
        puts = opt.puts.copy()
        puts['expirationDate'] = exp
        options_data[exp] = puts

    return options_data

# Build a copy button table (aligned with contracts)
def build_copy_table(contracts):
    copy_table = pd.DataFrame({
        "Copy": [
            f"""<button onclick="navigator.clipboard.writeText('{c}')">Copy</button>"""
            for c in contracts
        ]
    })
    return copy_table

def display_put_options_all_dates(ticker_symbol, stock_price):
    options_data = fetch_put_options(ticker_symbol)

    for exp, puts in options_data.items():
        puts = puts[['contractSymbol', 'lastPrice', 'bid', 'ask', 'strike', 'volume', 'openInterest']]
        puts.rename(columns={
            'contractSymbol': 'Contract',
            'lastPrice': 'Last Price',
            'bid': 'Bid',
            'ask': 'Ask',
            'strike': 'Strike',
            'volume': 'Volume',
            'openInterest': 'Open Interest'
        }, inplace=True)

        # Calculate max loss columns
        puts = calculate_max_loss(stock_price, puts)

        # Make a second table with copy buttons
        copy_table = build_copy_table(puts["Contract"])

        # Align side-by-side
        col1, col2 = st.columns([4,1])
        with col1:
            st.subheader(f"Options Expiring: {exp}")
            st.dataframe(puts, use_container_width=True)
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)  # add spacing
            st.write(copy_table.to_html(escape=False, index=False), unsafe_allow_html=True)

def main():
    st.title("Married Put Strategy Calculator")

    ticker_symbol = st.text_input("Enter the ticker symbol:", "").upper().strip()

    # Display the long name of the ticker symbol
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
