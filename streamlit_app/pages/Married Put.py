import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
from datetime import datetime

# Set Streamlit page configuration
st.set_page_config(page_title="Married Put", layout="wide")

NUMBER_OF_SHARES = 100  # standard options contract size

def calculate_max_loss(stock_price, options_table):
    """
    Max Loss = (Strike×100) - (Cost of Stock + Cost of Put)
    """
    # Ask-based
    options_table['Cost of Put (Ask)'] = options_table['Ask'] * NUMBER_OF_SHARES
    options_table['Max Loss (Ask)'] = (
        (options_table['Strike'] * NUMBER_OF_SHARES)
        - (stock_price * NUMBER_OF_SHARES + options_table['Cost of Put (Ask)'])
    )
    options_table['Max Loss Calc (Ask)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f} × {NUMBER_OF_SHARES}) - ({stock_price * NUMBER_OF_SHARES:.2f} + {row['Cost of Put (Ask)']:.2f})",
        axis=1
    )

    # Last-based
    options_table['Cost of Put (Last)'] = options_table['Last Price'] * NUMBER_OF_SHARES
    options_table['Max Loss (Last)'] = (
        (options_table['Strike'] * NUMBER_OF_SHARES)
        - (stock_price * NUMBER_OF_SHARES + options_table['Cost of Put (Last)'])
    )
    options_table['Max Loss Calc (Last)'] = options_table.apply(
        lambda row: f"({row['Strike']:.2f} × {NUMBER_OF_SHARES}) - ({stock_price * NUMBER_OF_SHARES:.2f} + {row['Cost of Put (Last)']:.2f})",
        axis=1
    )
    return options_table

def days_left(expiration_date_str: str) -> int:
    today = datetime.today().date()
    exp = datetime.strptime(expiration_date_str, "%Y-%m-%d").date()
    return (exp - today).days

def _html_escape(s: str) -> str:
    return (s
            .replace("&","&amp;")
            .replace("<","&lt;")
            .replace(">","&gt;")
            .replace('"',"&quot;")
            .replace("'","&#39;"))

def render_with_copy_buttons(df: pd.DataFrame, height_hint: int = 420):
    """
    Render a compact HTML table with a 'Copy' button next to each Contract.
    Uses navigator.clipboard; works in Streamlit without extra packages.
    """
    # Choose display columns and order
    cols = [
        "Contract", "Strike", "Last Price", "Bid", "Ask",
        "Volume", "Open Interest", "Implied Volatility",
        "Max Loss (Ask)", "Max Loss (Last)", "Expiration Date"
    ]
    df = df.loc[:, [c for c in cols if c in df.columns]].copy()

    # Build HTML
    rows_html = []
    for _, r in df.iterrows():
        contract = str(r.get("Contract",""))
        contract_safe = _html_escape(contract)
        # Build cells
        cells = [
            f"""
            <div class="contract-cell">
              <span class="mono">{contract_safe}</span>
              <button class="copy-btn" onclick="navigator.clipboard.writeText('{contract_safe}'); this.textContent='Copied'; setTimeout(()=>this.textContent='Copy',900);">Copy</button>
            </div>
            """
        ]
        for c in cols[1:]:
            val = r.get(c, "")
            if isinstance(val, float):
                # Light formatting
                if "Volatility" in c:
                    txt = f"{val:.2%}"
                else:
                    txt = f"{val:.2f}"
            else:
                txt = str(val)
            cells.append(f"<div>{_html_escape(txt)}</div>")
        rows_html.append("<div class='tr'>" + "".join(cells) + "</div>")

    header_html = "".join([f"<div class='th'>{_html_escape(h)}</div>" for h in cols])
    html = f"""
    <style>
      .tbl {{
        display: grid;
        grid-auto-rows: minmax(28px, auto);
        border: 1px solid #e6e6e6;
        border-radius: 8px;
        overflow: hidden;
        font-size: 13.5px;
      }}
      .thead, .tr {{
        display: grid;
        grid-template-columns: 1.2fr 0.7fr 0.7fr 0.7fr 0.7fr 0.7fr 0.9fr 0.9fr 1fr 1fr 1fr;
        align-items: center;
      }}
      .thead {{
        position: sticky; top: 0; z-index: 2;
        background: #f7f7f9; font-weight: 600; border-bottom: 1px solid #e6e6e6;
      }}
      .th, .tr > div {{
        padding: 6px 8px; border-bottom: 1px solid #f0f0f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }}
      .contract-cell {{ display: flex; gap: 8px; align-items: center; }}
      .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
      .copy-btn {{
        font-size: 12px; padding: 2px 8px; border: 1px solid #d0d0d0; border-radius: 6px; background: #fff; cursor: pointer;
      }}
      .wrap {{
        height: {height_hint}px; overflow: auto; border-radius: 8px; border: 1px solid #e6e6e6;
      }}
    </style>
    <div class="wrap">
      <div class="tbl">
        <div class="thead">{header_html}</div>
        {''.join(rows_html)}
      </div>
    </div>
    """
    components.html(html, height=height_hint+24, scrolling=False)

def display_put_options_all_dates(ticker_symbol, stock_price):
    try:
        ticker = yf.Ticker(ticker_symbol)
        expiration_dates = ticker.options
        if not expiration_dates:
            st.error(f"No options data available for {ticker_symbol}.")
            return

        all_data = pd.DataFrame()

        for chosen_date in expiration_dates:
            rem_days = days_left(chosen_date)
            st.subheader(f"Expiration: {chosen_date} ({rem_days} days left)")

            chain = ticker.option_chain(chosen_date)
            puts = chain.puts
            if puts.empty:
                st.warning(f"No puts for {chosen_date}.")
                continue

            puts_table = puts[[
                "contractSymbol","strike","lastPrice","bid","ask",
                "volume","openInterest","impliedVolatility"
            ]].rename(columns={
                "contractSymbol":"Contract",
                "strike":"Strike",
                "lastPrice":"Last Price",
                "bid":"Bid",
                "ask":"Ask",
                "volume":"Volume",
                "openInterest":"Open Interest",
                "impliedVolatility":"Implied Volatility"
            })
            puts_table["Expiration Date"] = chosen_date

            puts_table = calculate_max_loss(stock_price, puts_table)
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # Render with copy buttons
            # Height heuristic: header + ~28px per row, capped
            h = min(520, 52 + 28 * len(puts_table))
            render_with_copy_buttons(puts_table, height_hint=h)

        if not all_data.empty:
            csv = all_data.to_csv(index=False)
            st.download_button(
                label="Download All Expiration Data (CSV)",
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
            long_name = yf.Ticker(ticker_symbol).info.get("longName", "N/A")
            st.write(f"**Company Name:** {long_name}")
        except Exception as e:
            st.warning(f"Unable to fetch company name: {e}")

    if not ticker_symbol:
        st.warning("Please enter a valid ticker symbol.")
        return

    try:
        hist = yf.Ticker(ticker_symbol).history(period="1d")
        current_price = hist["Close"].iloc[-1] if not hist.empty else 0.0
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
