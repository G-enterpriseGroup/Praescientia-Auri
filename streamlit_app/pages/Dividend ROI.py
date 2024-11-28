import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import yfinance as yf
import streamlit as st

def get_stock_price(ticker):
    """
    Fetch the current stock price for the given ticker using Yahoo Finance.
    """
    stock = yf.Ticker(ticker)
    market_data = stock.history(period='1d')
    if not market_data.empty:
        return market_data['Close'].iloc[-1]
    else:
        st.warning(f"Could not retrieve data for ticker: {ticker}")
        return 0.0

def get_annual_dividend(ticker, is_etf):
    """
    Fetch the annual dividend for the given ticker from stockanalysis.com.
    """
    url = f"https://stockanalysis.com/{'etf' if is_etf else 'stocks'}/{ticker}/dividend/"
    xpath = "/html/body/div/div[1]/div[2]/main/div[2]/div/div[2]/div[2]/div"
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(), options=options)
    
    try:
        driver.get(url)
        time.sleep(3)
        element = driver.find_element(By.XPATH, xpath)
        dividend_text = element.text
        annual_dividend = float(dividend_text.replace("$", "").strip())
    except Exception as e:
        st.error(f"Error fetching annual dividend: {e}")
        annual_dividend = 0.0
    finally:
        driver.quit()
    
    return annual_dividend

def is_etf_ticker(ticker):
    """
    Determine if the ticker represents an ETF using Yahoo Finance.
    """
    stock = yf.Ticker(ticker)
    info = stock.info
    quote_type = info.get('quoteType', '').lower()
    return 'etf' in quote_type

def calculate_projected_income(ticker, days, quantity):
    """
    Calculate the projected dividend income and related financial metrics.
    """
    stock_price = get_stock_price(ticker)
    is_etf = is_etf_ticker(ticker)
    annual_dividend = get_annual_dividend(ticker, is_etf)
    
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
