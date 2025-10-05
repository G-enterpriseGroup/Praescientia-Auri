import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="Married Put", layout="wide")

# --- Core Calculations ---
def calculate_max_loss(stock_price, options_table):
    """Calculate Max Loss for each option using both Ask Price and Last Price."""
    number_of_shares = 100  # Standard contract size

    # Ask Price Calculations
    options_table['Cost of Put (Ask)'] = options_table['Ask'] * number_of_shares
    options_table['Max Loss (Ask)'] = (
        (options_table['Strike'] * number_of_shares)
        - (stock_price * number_of_shares + options_table['Cost of Put (Ask)'])
    )
    options_table['Max Loss Calc (Ask)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f}×{number_of_shares}) - ({stock_price * number_of_shares:.2f} + {row['Cost of Put (Ask)']:.2f})",
        axis=1
    )

    # Last Price Calculations
    options_table['Cost of Put (Last)'] = options_table['Last Price'] * number_of_shares
    options_table['Max Loss (Last)'] = (
        (options_table['Strike'] * number_of_shares)
        - (stock_price * number_of_shares + options_table['Cost of Put (Last)'])
    )
    options_table['Max Loss Calc (Last)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f}×{number_of_shares}) - ({stock_price * number_of_shares:.2f} + {row['Cost of Put (Last)']:.2f})",
        axis=1
    )

    return options_table

def calculate_trading_days_left(expiration_date):
    """Calculate the total number of days left until expiration."""
    today = datetime.today()
    expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
    return (expiration_date - today).days

# --- Display Function ---
def display_put_options_all_dates(ticker_symbol, stock_price):
    try:
        ticker = yf.Ticker(ticker_symbol)
        expiration_dates = ticker.options
        if not expiration_dates:
            st.error(f"No options data available for {ticker_symbol}.")
            return

        all_data = pd.DataFrame()

        for chosen_date in expiration_dates:
            trading_days_left = calculate_trading_days_left(chosen_date)
            st.subheader(f"Expiration: {chosen_date} ({trading_days_left} days left)")

            # Fetch put options
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts
            if puts.empty:
                st.warning(f"No puts available for {chosen_date}.")
                continue

            # Prepare core columns
            puts_table = puts[[
                "contractSymbol", "strike", "lastPrice", "bid", "ask",
                "volume", "openInterest", "impliedVolatility"
            ]]
            puts_table.columns = [
                "CN", "STK", "LP", "BID", "ASK", "VOL", "OI", "IV"
            ]
            puts_table["EXP"] = chosen_date

            # Calculate Max Loss Columns
            puts_table = calculate_max_loss(stock_price, puts_table)

            # --- Rename all columns with short acronyms ---
            column_renames = {
                "Cost of Put (Ask)": "PUT$A",
                "Max Loss (Ask)": "MLA",
                "Max Loss Calc (Ask)": "MLC-A",
                "Cost of Put (Last)": "PUT$L",
                "Max Loss (Last)": "MLL",
                "Max Loss Calc (Last)": "MLC-L"
            }
            puts_table.rename(columns=column_renames, inplace=True)

            # Prepare condensed view
            display_table = puts_table.drop(
                columns=["LP", "BID", "ASK", "VOL", "OI", "IV", "EXP"]
            )

            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # Apply simple highlighting and mobile-optimized display
            styled_table = (
                display_table.style
                .highlight_max(subset=["MLA", "MLL"], color="#fffa99")
                .set_table_styles([
                    {"selector": "th", "props": [("font-size", "12px"), ("text-align", "center")]},
                    {"selector": "td", "props": [("font-size", "12px"), ("text-align", "center"), ("white-space", "nowrap")]}
                ])
            )

            st.dataframe(styled_table, use_container_width=True, height=400)

        # CSV download
        if not all_data.empty:
            csv = all_data.to_csv(index=False)
            st.download_button(
                label="⬇️ Download All Expirations (CSV)",
                data=csv,
                file_name=f"{ticker_symbol}_puts.csv",
                mime="text/csv",
            )
        else:
            st.warning(f"No put options data to display or download for {ticker_symbol}.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

# --- Main App ---
def main():
    st.title("📊 Married Put Analyzer (Compact View)")

    ticker_symbol = st.text_input("Enter Ticker:", "").upper().strip()

    if ticker_symbol:
        try:
            ticker = yf.Ticker(ticker_symbol)
            long_name = ticker.info.get("longName", "N/A")
            dividend_yield = ticker.info.get("dividendYield", 0)
            dividend_display = f"{dividend_yield*100:.2f}%" if dividend_yield else "N/A"
            st.markdown(f"**{long_name}**  |  🏦 Dividend Yield: **{dividend_display}**")
        except Exception as e:
            st.warning(f"Unable to fetch company info: {e}")

    if not ticker_symbol:
        st.warning("Please enter a valid ticker symbol.")
        return

    # Fetch stock price
    try:
        ticker = yf.Ticker(ticker_symbol)
        stock_info = ticker.history(period="1d")
        current_price = stock_info["Close"].iloc[-1] if not stock_info.empty else 0.0
    except Exception:
        current_price = 0.0

    stock_price = st.number_input(
        "Enter your stock purchase price:",
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
