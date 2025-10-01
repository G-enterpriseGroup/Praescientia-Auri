import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Set Streamlit page configuration
st.set_page_config(page_title="Married Put", layout="wide")

def calculate_max_loss(stock_price, options_table):
    number_of_shares = 100

    options_table['Cost of Put (Ask)'] = options_table['Ask'] * number_of_shares
    options_table['Max Loss (Ask)'] = (
        (options_table['Strike'] * number_of_shares) -
        (stock_price * number_of_shares + options_table['Cost of Put (Ask)'])
    )
    options_table['Max Loss Calc (Ask)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f} × {number_of_shares}) - ({stock_price * number_of_shares:.2f} + {row['Cost of Put (Ask)']:.2f})",
        axis=1
    )

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
    today = datetime.today()
    expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
    return (expiration_date - today).days

def contract_with_copy_button(contract_id: str, btn_id: str) -> str:
    return f"""
    <div style='display:flex; align-items:center; gap:6px;'>
      <span>{contract_id}</span>
      <button id='{btn_id}' title='Copy' style='
        background:#eee;
        border:1px solid #ccc;
        border-radius:4px;
        font-size:11px;
        padding:2px 5px;
        cursor:pointer;'>📋</button>
      <script>
        const btn = document.getElementById('{btn_id}');
        if (btn) {{
            btn.onclick = () => navigator.clipboard.writeText("{contract_id}");
        }}
      </script>
    </div>
    """

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

            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                st.warning(f"No puts available for expiration date {chosen_date}.")
                continue

            puts_table = puts[
                ["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]
            ].copy()

            puts_table.columns = [
                "Contract",
                "Strike",
                "Last Price",
                "Bid",
                "Ask",
                "Volume",
                "Open Interest",
                "Implied Volatility"
            ]
            puts_table["Expiration Date"] = chosen_date
            puts_table = calculate_max_loss(stock_price, puts_table)
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # ---- Replace "Contract" column values with HTML buttons inside ----
            puts_table["Contract"] = puts_table["Contract"].apply(
                lambda val: contract_with_copy_button(val, f"btn_{val}")
            )

            st.write(
                puts_table.to_html(escape=False, index=False),
                unsafe_allow_html=True
            )

        if not all_data.empty:
            csv = all_data.to_csv(index=False)
            st.download_button(
                label="Download All Expiration Data as CSV",
                data=csv,
                file_name=f"{ticker_symbol}_put_options.csv",
                mime="text/csv"
            )
        else:
            st.info("No data to download.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

def main():
    st.title("Married Put")

    ticker_symbol = st.text_input("Enter Ticker Symbol", value="SPOK").strip().upper()
    if not ticker_symbol:
        st.stop()

    try:
        current_price = yf.Ticker(ticker_symbol).history(period="1d")["Close"].iloc[-1]
    except Exception:
        current_price = 0.0

    stock_price = st.number_input(
        "Enter Current Stock Price",
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
