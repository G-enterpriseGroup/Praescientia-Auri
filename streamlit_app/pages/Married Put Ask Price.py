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


def highlight_ask_and_loss(writer, df, worksheet_name):
    """
    Apply Excel formatting to highlight rows:
    - Lime green for Max Loss closest to 0.
    - Red for rows where Ask = 0.
    """
    workbook = writer.book
    worksheet = writer.sheets[worksheet_name]

    # Define formatting
    lime_green = workbook.add_format({'bg_color': '#32CD32'})  # Lime Green
    red = workbook.add_format({'bg_color': '#FF6666'})         # Red

    # Find the row where Max Loss is closest to 0
    closest_to_zero_idx = df['Max Loss'].abs().idxmin()

    # Iterate over rows to apply formatting
    for row_num, (_, row) in enumerate(df.iterrows(), start=1):  # Start from 1 (Excel row)
        if row['Ask'] == 0:
            worksheet.set_row(row_num, None, red)  # Highlight entire row in red
        elif row.name == closest_to_zero_idx:
            worksheet.set_row(row_num, None, lime_green)  # Highlight entire row in lime green


def download_data_with_formatting(data):
    """Generate a downloadable Excel file with formatting."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, index=False, sheet_name="Options Data")
        highlight_ask_and_loss(writer, data, "Options Data")
    output.seek(0)  # Ensure the pointer is reset to the start of the buffer
    return output


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


def main():
    st.title("Options Analysis with Max Loss Calculation (Using Ask Price)")

    # Input for ticker symbol
    ticker_symbol = st.text_input("Enter the ticker symbol:", "").upper().strip()
    if ticker_symbol:
        try:
            # Fetch current stock price
            stock = yf.Ticker(ticker_symbol)
            current_price = stock.history(period="1d")['Close'].iloc[-1]
        except Exception:
            current_price = 0
            st.warning("Could not fetch the current stock price. Please enter it manually.")

        # Input for purchase price per share (auto-filled with fetched price)
        stock_price = st.number_input(
            "Enter the purchase price per share of the stock:",
            value=float(current_price) if current_price else 0.0,
            min_value=0.0
        )

        # Fetch and display options data
        if st.button("Fetch Options Data"):
            combined_data = display_put_options_all_dates(ticker_symbol, stock_price)

            if combined_data is not None:
                # Offer the data for download with formatting
                st.subheader("Download Data")
                excel_data = download_data_with_formatting(combined_data)
                st.download_button(
                    label="Download Options Data as Excel",
                    data=excel_data,
                    file_name=f"{ticker_symbol}_options_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


if __name__ == "__main__":
    main()
