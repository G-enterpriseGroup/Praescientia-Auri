import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json

# Set Streamlit page configuration
st.set_page_config(page_title="Married Put", layout="wide")

NUMBER_OF_SHARES = 100  # Standard contract size

def calculate_max_loss(stock_price, options_table):
    """
    Calculate Max Loss for each option using both Ask Price and Last Price:
    Max Loss = (Strike Price × 100) - (Cost of Stock + Cost of Put)
    """
    # Ask-based
    options_table['Cost of Put (Ask)'] = options_table['Ask'] * NUMBER_OF_SHARES
    options_table['Max Loss (Ask)'] = (
        (options_table['Strike'] * NUMBER_OF_SHARES) -
        (stock_price * NUMBER_OF_SHARES + options_table['Cost of Put (Ask)'])
    )
    options_table['Max Loss Calc (Ask)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f} × {NUMBER_OF_SHARES}) - ({stock_price * NUMBER_OF_SHARES:.2f} + {row['Cost of Put (Ask)']:.2f})",
        axis=1
    )

    # Last-based
    options_table['Cost of Put (Last)'] = options_table['Last Price'] * NUMBER_OF_SHARES
    options_table['Max Loss (Last)'] = (
        (options_table['Strike'] * NUMBER_OF_SHARES) -
        (stock_price * NUMBER_OF_SHARES + options_table['Cost of Put (Last)'])
    )
    options_table['Max Loss Calc (Last)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f} × {NUMBER_OF_SHARES}) - ({stock_price * NUMBER_OF_SHARES:.2f} + {row['Cost of Put (Last)']:.2f})",
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

# ---------- Helper: tiny clipboard bridge (used by both modes) ----------
def _queue_copy(text: str):
    st.session_state["_copy_text"] = text

def _flush_copy_js():
    txt = st.session_state.pop("_copy_text", None)
    if txt is not None:
        components.html(
            f"<script>navigator.clipboard.writeText({json.dumps(txt)});</script>",
            height=0,
        )
        st.toast(f"Copied: {txt}")

# ---------- Fallback mini copy list (only shown if data_editor ButtonColumn unavailable) ----------
def render_contract_copy_panel(puts_table, exp_key: str):
    st.caption("Quick copy (contract symbols):")
    for i, c in enumerate(puts_table["Contract"].astype(str).tolist()):
        cols = st.columns([1, 0.12])
        cols[0].write(c)
        if cols[1].button("Copy", key=f"copy_{exp_key}_{i}"):
            _queue_copy(c)
    _flush_copy_js()

def _has_button_column():
    # Detect availability of ButtonColumn in this Streamlit version
    try:
        _ = st.column_config.ButtonColumn
        return True
    except Exception:
        return False

def display_put_options_all_dates(ticker_symbol, stock_price):
    try:
        ticker = yf.Ticker(ticker_symbol)
        expiration_dates = ticker.options
        if not expiration_dates:
            st.error(f"No options data available for ticker {ticker_symbol}.")
            return

        all_data = pd.DataFrame()
        can_inline_copy = _has_button_column()

        for chosen_date in expiration_dates:
            trading_days_left = calculate_trading_days_left(chosen_date)
            st.subheader(f"Expiration Date: {chosen_date} ({trading_days_left} trading days left)")

            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts
            if puts.empty:
                st.warning(f"No puts available for expiration date {chosen_date}.")
                continue

            # Prepare put options table
            puts_table = puts[[
                "contractSymbol", "strike", "lastPrice", "bid", "ask",
                "volume", "openInterest", "impliedVolatility"
            ]].rename(columns={
                "contractSymbol": "Contract",
                "strike": "Strike",
                "lastPrice": "Last Price",
                "bid": "Bid",
                "ask": "Ask",
                "volume": "Volume",
                "openInterest": "Open Interest",
                "impliedVolatility": "Implied Volatility"
            })
            puts_table["Expiration Date"] = chosen_date

            # Calculate max loss
            puts_table = calculate_max_loss(stock_price, puts_table)

            # Append
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # ----- Render table with inline Copy button in col 1 (if supported) -----
            if can_inline_copy:
                display_cols = [
                    "Contract", "Copy", "Strike", "Last Price", "Bid", "Ask",
                    "Volume", "Open Interest", "Implied Volatility",
                    "Expiration Date", "Cost of Put (Ask)", "Max Loss (Ask)", "Max Loss Calc (Ask)",
                    "Cost of Put (Last)", "Max Loss (Last)", "Max Loss Calc (Last)"
                ]
                display_df = puts_table.copy()
                # Duplicate contract into a column that will host the button
                display_df.insert(1, "Copy", display_df["Contract"])

                st.data_editor(
                    display_df[display_cols],
                    hide_index=True,
                    disabled=True,               # keeps it read-only like dataframe
                    use_container_width=True,
                    column_config={
                        "Copy": st.column_config.ButtonColumn(
                            "Copy",
                            help="Copy contract symbol",
                            width="small",
                            on_click=_queue_copy,   # cell value passed automatically
                        ),
                    },
                    key=f"editor_{chosen_date}",
                )
                _flush_copy_js()
            else:
                # Keep your original st.dataframe look, then add a tiny copy panel under it
                styled_table = puts_table.style.highlight_max(
                    subset=["Max Loss (Ask)", "Max Loss (Last)"], color="yellow"
                )
                st.dataframe(styled_table, use_container_width=True)
                render_contract_copy_panel(puts_table, exp_key=chosen_date)

        if not all_data.empty:
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

    # Current price default
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
