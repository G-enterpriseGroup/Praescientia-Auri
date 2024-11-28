import streamlit as st
import yfinance as yf
import requests
from lxml import html

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
    total_cost = stock_price * quantity
    dividend_yield = (annual_dividend / stock_price) * 100 if stock_price else 0
    daily_dividend_rate = annual_dividend / 365
    projected_income = daily_dividend_rate * days * quantity
    
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
