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
    try:
        stock = yf.Ticker(ticker)
        market_data = stock.history(period='1d')
        if not market_data.empty:
            return float(market_data['Close'].iloc[-1])
    except Exception:
        pass
    return None

def get_full_security_name(ticker):
    """
    Fetch the full security name for the given ticker using Yahoo Finance.
    Args:
        ticker (str): The ticker symbol.
    Returns:
        str: The full security name.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        return info.get('longName', 'N/A')
    except Exception:
        return 'N/A'

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
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            # XPath from your original code
            annual_dividend = tree.xpath('/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div/text()')
            if annual_dividend:
                return float(annual_dividend[0].replace("$", "").strip())
    except Exception:
        pass
    return 0.0

def is_etf_ticker(ticker):
    """
    Determine if the ticker represents an ETF using Yahoo Finance.
    Args:
        ticker (str): The ticker symbol.
    Returns:
        bool: True if it's an ETF, False otherwise.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        quote_type = str(info.get('quoteType', '')).lower()
        return 'etf' in quote_type
    except Exception:
        return False

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

    etf_flag = is_etf_ticker(ticker)
    annual_dividend = get_annual_dividend(ticker, etf_flag)
    security_name = get_full_security_name(ticker)

    total_cost = stock_price * quantity
    dividend_yield = (annual_dividend / stock_price) * 100 if stock_price else 0
    daily_dividend_rate = annual_dividend / 365
    projected_income = total_cost * (daily_dividend_rate / stock_price) * days

    return {
        'security_name': security_name,
        'projected_income': projected_income,
        'stock_price': stock_price,
        'total_cost': total_cost,
        'dividend_yield': dividend_yield
    }

# ---------------- Streamlit UI ----------------
st.title("Dividend Income Calculator")

ticker = st.text_input("Enter the Ticker Symbol:").strip().upper()
# Free tier: exactly as before (minimum 366), and block anything > 366
days = st.number_input("Enter the Number of Days to Hold (Free up to 366):", min_value=366, step=1)
quantity = st.number_input("Enter the Quantity of Shares Held:", min_value=100, step=1)

if st.button("Calculate"):
    if not ticker:
        st.warning("Please enter a valid ticker symbol.")
    elif days > 366:
        st.info("Pro feature: Holding periods above 366 days require an upgrade.")
    else:
        results = calculate_projected_income(ticker, int(days), int(quantity))
        if "error" in results:
            st.error(results["error"])
        else:
            st.subheader(f"Financial Summary for {ticker}")
            st.write(f"**Security Name:** {results['security_name']}")
            st.write(f"**Current Stock Price:** ${results['stock_price']:.2f}")
            st.write(f"**Total Investment Cost:** ${results['total_cost']:.2f}")
            st.write(f"**Dividend Yield:** {results['dividend_yield']:.2f}%")
            st.write(f"**Projected Dividend Income over {int(days)} days:** ${results['projected_income']:.2f}")
