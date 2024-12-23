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


from datetime import datetime

def calculate_trading_days_left(expiration_date):
    """
    Calculate the total number of days left until the expiration date.
    """
    today = datetime.today()
    expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
    return (expiration_date - today).days


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

            # Append data to main DataFrame
            all_data = pd.concat([all_data, puts_table], ignore_index=True)

            # Highlight Max Loss columns
            styled_table = puts_table.style.highlight_max(
                subset=["Max Loss (Ask)", "Max Loss (Last)"], color="yellow"
            )
            st.dataframe(styled_table)

        if not all_data.empty:
            # Allow downloading the complete table as a CSV file
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

    # Input for ticker symbol
    ticker_symbol = st.text_input("Enter the ticker symbol:", "").upper().strip()
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
_______________________________________________________________________________________________________________________________________________________________________

import streamlit as st
import yfinance as yf
import requests
from lxml import html
st.set_page_config(page_title="Dividend Income Calculator")
def get_stock_price(ticker):
    """
    Fetch the current stock price for the given ticker using Yahoo Finance.
    Args:
        ticker (str): The ticker symbol.
    Returns:
        float: The current stock price.
    """
    stock = yf.Ticker(ticker)
    market_data = stock.history(period='1d')
    if not market_data.empty:
        return market_data['Close'].iloc[-1]
    else:
        return None

def get_full_security_name(ticker):
    """
    Fetch the full security name for the given ticker using Yahoo Finance.
    Args:
        ticker (str): The ticker symbol.
    Returns:
        str: The full security name.
    """
    stock = yf.Ticker(ticker)
    return stock.info.get('longName', 'N/A')

def get_annual_dividend(ticker, is_etf):
    """
    Fetch the annual dividend for the given ticker from stockanalysis.com using lxml.
    Args:
        ticker (str): The ticker symbol.
        is_etf (bool): Whether the ticker represents an ETF or a stock.
    Returns:
        float: The annual dividend amount per share.
    """
    base_url = "https://stockanalysis.com"
    url = f"{base_url}/{'etf' if is_etf else 'stocks'}/{ticker}/dividend/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')
            if annual_dividend:
                return float(annual_dividend[0].replace("$", "").strip())
        return 0.0
    except Exception:
        return 0.0

def is_etf_ticker(ticker):
    """
    Determine if the ticker represents an ETF using Yahoo Finance.
    Args:
        ticker (str): The ticker symbol.
    Returns:
        bool: True if it's an ETF, False otherwise.
    """
    stock = yf.Ticker(ticker)
    info = stock.info
    quote_type = info.get('quoteType', '').lower()
    return 'etf' in quote_type

def calculate_projected_income(ticker, days, quantity):
    """
    Calculate the projected dividend income and related financial metrics.
    Args:
        ticker (str): The ticker symbol.
        days (int): Number of days the security is held.
        quantity (int): Number of shares held.
    Returns:
        dict: Contains projected income, stock price, total cost, dividend yield percentage, and security name.
    """
    stock_price = get_stock_price(ticker)
    if stock_price is None:
        return {"error": f"Could not fetch stock price for {ticker}"}

    is_etf = is_etf_ticker(ticker)
    annual_dividend = get_annual_dividend(ticker, is_etf)
    security_name = get_full_security_name(ticker)
    
    # Calculate financial metrics
    total_cost = stock_price * quantity  # Total investment cost
    dividend_yield = (annual_dividend / stock_price) * 100 if stock_price else 0  # Annual dividend yield percentage
    daily_dividend_rate = annual_dividend / 365  # Daily dividend rate
    projected_income = total_cost * (daily_dividend_rate / stock_price) * days  # Projected income based on daily dividends

    
    return {
        'security_name': security_name,
        'projected_income': projected_income,
        'stock_price': stock_price,
        'total_cost': total_cost,
        'dividend_yield': dividend_yield
    }

# Streamlit UI
st.title("Dividend Income Calculator")

# Input fields
ticker = st.text_input("Enter the Ticker Symbol:").strip().upper()
days = st.number_input("Enter the Number of Days to Hold:", min_value=366, step=1)
quantity = st.number_input("Enter the Quantity of Shares Held:", min_value=100, step=1)

# Calculation
if st.button("Calculate"):
    if ticker:
        results = calculate_projected_income(ticker, days, quantity)
        if "error" in results:
            st.error(results["error"])
        else:
            st.subheader(f"Financial Summary for {ticker}")
            st.write(f"**Security Name:** {results['security_name']}")
            st.write(f"**Current Stock Price:** ${results['stock_price']:.2f}")
            st.write(f"**Total Investment Cost:** ${results['total_cost']:.2f}")
            st.write(f"**Dividend Yield:** {results['dividend_yield']:.2f}%")
            st.write(f"**Projected Dividend Income over {days} days:** ${results['projected_income']:.2f}")
    else:
        st.warning("Please enter a valid ticker symbol.")
