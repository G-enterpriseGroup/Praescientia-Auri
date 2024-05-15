import streamlit as st
import yfinance as yf

def get_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5y")
    ex_divs = stock.dividends
    return hist, ex_divs

def calculate_difference(hist, ex_date):
    if ex_date in hist.index:
        day_data = hist.loc[ex_date]
        return day_data['High'] - day_data['Low']
    return None

st.title('Ex-Dividend Price Difference Calculator')

ticker = st.text_input('Enter the ticker symbol:', 'PULS')

if ticker:
    hist, ex_divs = get_data(ticker)
    if not ex_divs.empty:
        ex_date = ex_divs.idxmax()  # Assumes the latest ex-dividend date is most relevant
        price_diff = calculate_difference(hist, ex_date)
        if price_diff is not None:
            st.write(f"Ex-dividend date: {ex_date.date()}")
            st.write(f"Price difference between high and low on {ex_date.date()}: ${price_diff:.2f}")
        else:
            st.write("No trading data available for the ex-dividend date.")
    else:
        st.write("No ex-dividend dates found for this ticker.")
