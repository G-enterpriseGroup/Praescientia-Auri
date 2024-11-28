import yfinance as yf
import streamlit as st

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
        st.warning(f"Could not retrieve data for ticker: {ticker}")
        return 0.0

def get_annual_dividend(ticker):
    """
    Fetch the annual dividend for the given ticker using Yahoo Finance.
    Args:
        ticker (str): The ticker symbol.
    Returns:
        float: The annual dividend amount per share.
    """
    stock = yf.Ticker(ticker)
    dividend_info = stock.info.get("dividendRate", 0.0)
    if dividend_info is None:
        dividend_info = 0.0
    return dividend_info

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
        dict: Contains projected income, stock price, total cost, and dividend yield percentage.
    """
    stock_price = get_stock_price(ticker)
    annual_dividend = get_annual_dividend(ticker)
    
    # Calculate financial metrics
    total_cost = stock_price * quantity
    dividend_yield = (annual_dividend / stock_price) * 100 if stock_price else 0
    daily_dividend_rate = annual_dividend / 365
    projected_income = daily_dividend_rate * days * quantity
    
    return {
        'projected_income': projected_income,
        'stock_price': stock_price,
        'total_cost': total_cost,
        'dividend_yield': dividend_yield
    }

# Streamlit UI
st.title("Dividend Income Calculator")

# User Inputs
ticker = st.text_input("Enter the ticker symbol:", "").strip().upper()
days = st.number_input("Enter the number of days you plan to hold the security:", min_value=1, value=30)
quantity = st.number_input("Enter the quantity of securities you are holding:", min_value=1, value=10)

# Button to Calculate
if st.button("Calculate"):
    if ticker:
        results = calculate_projected_income(ticker, days, quantity)
        st.subheader(f"Financial Summary for {ticker}:")
        st.write(f"**Current Stock Price:** ${results['stock_price']:.2f}")
        st.write(f"**Total Investment Cost:** ${results['total_cost']:.2f}")
        st.write(f"**Dividend Yield:** {results['dividend_yield']:.2f}%")
        st.write(f"**Projected Dividend Income over {days} days:** ${results['projected_income']:.2f}")
    else:
        st.warning("Please enter a valid ticker symbol.")

