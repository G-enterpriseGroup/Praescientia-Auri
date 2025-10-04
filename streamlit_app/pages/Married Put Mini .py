import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Configure Streamlit for mobile responsiveness
st.set_page_config(page_title="Married Put", layout="wide")

# Apply compact mobile-friendly CSS
st.markdown("""
    <style>
    /* Make dataframe tables responsive and compact */
    .stDataFrame, .stTable {
        overflow-x: auto;
        width: 100%;
    }
    [data-testid="stDataFrame"] table {
        font-size: 12px !important;
        white-space: nowrap !important;
    }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
        padding: 2px 6px !important;
    }
    [data-testid="stDataFrame"] th {
        font-weight: 600 !important;
    }
    /* Reduce Streamlit padding for mobile view */
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


def format_number(x):
    """Format numbers to remove unnecessary trailing zeros while keeping up to 2 decimals."""
    if isinstance(x, (int, float)):
        return f"{x:.2f}".rstrip('0').rstrip('.')
    return x


def calculate_max_loss(stock_price, options_table):
    """Calculate Max Loss for each option using both Ask and Last prices."""
    number_of_shares = 100  # Standard contract size

    # Perform calculations using the Ask Price
    options_table['Cost of Put (Ask)'] = options_table['Ask'] * number_of_shares
    options_table['Max Loss (Ask)'] = (
        (options_table['Strike'] * number_of_shares)
        - (stock_price * number_of_shares + options_table['Cost of Put (Ask)'])
    )
    options_table['Max Loss Calc (Ask)'] = options_table.apply(
        lambda row: f"({format_number(row['Strike'])} × {number_of_shares}) - ({format_number(stock_price * number_of_shares)} + {format_number(row['Cost of Put (Ask)'])})",
        axis=1
    )

    # Perform calculations using the Last Price
    options_table['Cost of Put (Last)'] = options_table['Last Price'] * number_of_shares
    options_table['Max Loss (Last)'] = (
        (options_table['Strike'] * number_of_shares)
        - (stock_price * number_of_shares + options_table['Cost of Put (Last)'])
    )
    options_table['Max Loss Calc (Last)'] = options_table.apply(
        lambda row: f"({format_number(row['Strike'])} × {number_of_shares}) - ({format_number(stock_price * number_of_shares)} + {format_number(row['Cost of Put (Last)'])})",
        axis=1
    )

    # Round internally to 2 decimals
    for col in options_table.select_dtypes(include=['float', 'int']).columns:
        options_table[col] = options_table[col].round(2)

    return options_table


def calculate_trading_days_left(expiration_date):
    """Calculate days left until expiration."""
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
            st.markdown(f"### Expiration: {chosen_date} ({trading_days_left} days left)")

            # Fetch put options
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                st.warning(f"No puts available for expiration date {chosen_date}.")
                continue

            # Prepare data
            puts_table = puts[["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]]
            puts_table.columns = ["Contract", "Strike", "Last Price", "Bid", "Ask", "Volume", "Open Interest", "Implied Volatility"]
            puts_table["Expiration Date"] = chosen_date

            # Run max loss calc
            puts_table = calculate_max_loss(stock_price, puts_table)

            # Hide unwanted columns
            display_table = puts_table.drop(
                columns=[
                    "Last Price", "Bid", "Ask", "Volume", "Open Interest",
                    "Implied Volatility", "Expiration Date", "Contract",
                    "Max Loss Calc (Ask)", "Max Loss Calc (Last)"
                ]
            )

            # Apply clean number formatting
            display_table = display_table.map(format_number)

            # Append all data for CSV
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # Highlight max loss visually (still compact)
            styled_table = display_table.style.highlight_max(
                subset=["Max Loss (Ask)", "Max Loss (Last)"], color="lightyellow"
            )

            # Display table with small height and scrollable view
            st.dataframe(
                styled_table,
                use_container_width=True,
                height=350
            )

        if not all_data.empty:
            csv = all_data.to_csv(index=False)
            st.download_button(
                label="📥 Download All Expiration Data (CSV)",
                data=csv,
                file_name=f"{ticker_symbol}_put_options.csv",
                mime="text/csv",
            )
        else:
            st.warning("No put options data available to display or download.")

    except Exception as e:
        st.error(f"An error occurred: {e}")


def main():
    st.title("📊 Married Put Options (Mobile Optimized)")

    ticker_symbol = st.text_input("Enter ticker symbol:", "").upper().strip()

    if ticker_symbol:
        try:
            ticker = yf.Ticker(ticker_symbol)
            long_name = ticker.info.get("longName", "N/A")
            st.markdown(f"**Company:** {long_name}")
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
        "Enter stock purchase price ($):",
        min_value=0.0,
        value=float(current_price),
        step=0.01
    )

    if stock_price <= 0:
        st.warning("Please enter a valid stock price.")
        return

    if st.button("📈 Fetch Options Data"):
        display_put_options_all_dates(ticker_symbol, stock_price)


if __name__ == "__main__":
    main()
