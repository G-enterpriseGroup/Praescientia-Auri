import streamlit as st
import streamlit.components.v1 as components
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
    options_table["Cost of Put (Ask)"] = (options_table["Ask"] * number_of_shares).round(6)
    options_table["Max Loss (Ask)"] = (
        (options_table["Strike"] * number_of_shares)
        - (stock_price * number_of_shares + options_table["Cost of Put (Ask)"])
    ).round(6)

    # Perform calculations using the Last Price
    options_table["Cost of Put (Last)"] = (options_table["Last Price"] * number_of_shares).round(6)
    options_table["Max Loss (Last)"] = (
        (options_table["Strike"] * number_of_shares)
        - (stock_price * number_of_shares + options_table["Cost of Put (Last)"])
    ).round(6)

    # Preserve your column order
    options_table = options_table[
        [
            "Contract",
            "Strike",
            "Last Price",
            "Bid",
            "Ask",
            "Volume",
            "Open Interest",
            "Implied Volatility",
            "Expiration Date",
            "Cost of Put (Ask)",
            "Max Loss (Ask)",
            "Cost of Put (Last)",
            "Max Loss (Last)",
        ]
    ]
    return options_table

def calculate_trading_days_left(expiration_date):
    today = datetime.today()
    expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
    return (expiration_date - today).days

# ------- NEW: compact, perfectly aligned “Copy” table (one column) ----------
def copy_table_html(contracts, row_px=30, header_px=34, border_radius=12):
    """
    Returns HTML for a single-column table with one row per contract,
    each row containing a clipboard button that copies that contract.
    Heights are fixed so rows align visually with the options table.
    """
    # Build rows
    rows_html = []
    for i, c in enumerate(contracts):
        btn_id = f"cp_{i}"
        rows_html.append(f"""
        <tr style="height:{row_px}px">
          <td style="padding:0 6px;">
            <button id="{btn_id}" title="Copy"
              style="cursor:pointer; border:1px solid #3a3a3a; background:#222;
                     padding:2px 6px; border-radius:8px; font-size:12px;">
              📋
            </button>
            <script>
              (function(){{
                const b=document.getElementById("{btn_id}");
                if (b) b.onclick = () => navigator.clipboard.writeText("{c}");
              }})();
            </script>
          </td>
        </tr>
        """)

    table_html = f"""
    <div style="display:inline-block;">
      <table style="
          border-collapse:separate;
          border-spacing:0;
          background:#0f1116;
          color:#e6e6e6;
          border:1px solid #2a2a2a;
          border-radius:{border_radius}px;
          overflow:hidden;">
        <thead>
          <tr style="height:{header_px}px; background:#171a21; border-bottom:1px solid #2a2a2a;">
            <th style="font-weight:600; padding:0 8px; text-align:center;">Copy</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </div>
    """
    return table_html

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

            # Prepare put options table
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
                "Implied Volatility",
            ]
            puts_table["Expiration Date"] = chosen_date

            # Calculate max loss for each option
            puts_table = calculate_max_loss(stock_price, puts_table)
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # Your existing styling
            styled_table = (
                puts_table.style
                .format({
                    "Strike": "{:.2f}",
                    "Last Price": "{:.6f}",
                    "Bid": "{:.6f}",
                    "Ask": "{:.6f}",
                    "Volume": "{:,.0f}",
                    "Open Interest": "{:,.0f}",
                    "Implied Volatility": "{:.6f}",
                    "Cost of Put (Ask)": "{:.6f}",
                    "Max Loss (Ask)": "{:.6f}",
                    "Cost of Put (Last)": "{:.6f}",
                    "Max Loss (Last)": "{:.6f}",
                })
                .hide(axis="index")
                .set_properties(**{"text-align": "right"})
                .set_properties(subset=["Contract"], **{"text-align": "left"})
                .highlight_between(subset=["Max Loss (Ask)", "Max Loss (Last)"], color="yellow")
            )

            # --------- Layout: left = new one-column "Copy" table, right = your table ----------
            left, right = st.columns([0.08, 0.92])
            with left:
                # Row/ header heights tuned to match Streamlit table defaults; tweak if needed.
                components.html(copy_table_html(puts_table["Contract"].tolist(),
                                                row_px=30, header_px=34, border_radius=12),
                                height=34 + 30*len(puts_table), scrolling=False)
            with right:
                st.dataframe(styled_table, use_container_width=True)
            # ------------------------------------------------------------------------------------

        if not all_data.empty:
            csv = all_data.to_csv(index=False)
            st.download_button(
                label="Download All Expiration Data as CSV",
                data=csv,
                file_name=f"{ticker_symbol}_put_options.csv",
                mime="text/csv",
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
