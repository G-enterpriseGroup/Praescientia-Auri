import streamlit as st
import yfinance as yf
import pandas as pd
from io import BytesIO


def calculate_max_loss(stock_price, options_table):
    """
    Calculate Max Loss for each option:
    Max Loss = (Strike Price × 100) - (Cost of Stock + Cost of Put)
    """
    number_of_shares = 100  # Standard contract size

    # Make a copy of the DataFrame to avoid SettingWithCopyWarning
    options_table = options_table.copy()

    # Perform calculations using the Ask Price
    options_table['Cost of Put'] = options_table['Ask'] * number_of_shares
    options_table['Cost of Stock'] = stock_price * number_of_shares
    options_table['Max Loss'] = (
        (options_table['Strike'] * number_of_shares) -
        (options_table['Cost of Stock'] + options_table['Cost of Put'])
    )
    # Add a column to display the calculation steps
    options_table['Max Loss Calc'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f} × {number_of_shares}) - ({row['Cost of Stock']:.2f} + {row['Cost of Put']:.2f})",
        axis=1
    )
    return options_table


def display_put_options_all_dates(ticker_symbol, stock_price):
    combined_data = []
    try:
        # Fetch Ticker object
        ticker = yf.Ticker(ticker_symbol)
        
        # Fetch available expiration dates
        expiration_dates = ticker.options
        if not expiration_dates:
            st.error(f"No options data available for ticker {ticker_symbol}.")
            return None

        for chosen_date in expiration_dates:
            with st.expander(f"Expiration Date: {chosen_date}", expanded=False):
                # Fetch put options for the current expiration date
                options_chain = ticker.option_chain(chosen_date)
                puts = options_chain.puts

                if puts.empty:
                    st.warning(f"No puts available for expiration date {chosen_date}.")
                    continue
                
                # Prepare put options table
                puts_table = puts[["contractSymbol", "strike", "ask", "bid", "volume", "openInterest", "impliedVolatility"]]
                puts_table.columns = ["Contract", "Strike", "Ask", "Bid", "Volume", "Open Interest", "Implied Volatility"]
                
                # Calculate max loss for each option using the Ask Price
                puts_table = calculate_max_loss(stock_price, puts_table)
                puts_table['Expiration Date'] = chosen_date  # Add expiration date for clarity
                
                # Append data to the combined list
                combined_data.append(puts_table)
                
                # Display the table
                st.dataframe(puts_table)

        # Combine all data into a single DataFrame
        if combined_data:
            combined_df = pd.concat(combined_data, ignore_index=True)
            return combined_df
        else:
            st.warning("No options data available for the given ticker and stock price.")
            return None

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None


def download_data(data):
    """Generate a downloadable Excel file."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, index=False, sheet_name="Options Data")
        writer.save()
    output.seek(0)
    return output


def main():
    st.title("Options Analysis with Max Loss Calculation (Using Ask Price)")

    # Input for ticker symbol
    ticker_symbol = st.text_input("Enter the ticker symbol:", "").upper().strip()
    if not ticker_symbol:
        st.warning("Please enter a valid ticker symbol.")
        return

    # Input for purchase price per share
    try:
        stock_price = st.number_input("Enter the purchase price per share of the stock:", min_value=0.0)
        if stock_price <= 0:
            st.warning("Please enter a valid stock price.")
            return
    except ValueError:
        st.error("Please enter a numeric value for the stock price.")
        return

    # Fetch and display options data
    if st.button("Fetch Options Data"):
        combined_data = display_put_options_all_dates(ticker_symbol, stock_price)

        if combined_data is not None:
            # Offer the data for download
            st.subheader("Download Data")
            excel_data = download_data(combined_data)
            st.download_button(
                label="Download Options Data as Excel",
                data=excel_data,
                file_name=f"{ticker_symbol}_options_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


if __name__ == "__main__":
    main()
