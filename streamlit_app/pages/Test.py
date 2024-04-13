import streamlit as st
import yfinance as yf
from datetime import datetime

# Title and date input
st.title("DivFinancial Dashboard")
"""The dashboard simplifies the process of tracking investment performance by calculating essential financial indicators like cost value, market value, profit or loss, and potential dividend income. It helps investors understand how long it will take to recover their investments through dividends, offering a clear view of both short-term performance and long-term income potential. This tool is particularly useful for those who need to manage multiple stocks and want to assess their portfolio's health quickly and accurately.
"""
today_date = st.date_input("Today's Date", datetime.now())

# Ticker input and data fetching
ticker_input = st.text_input("Enter Stock Ticker", value='ABR')

def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")['Close'].iloc[-1]  # Latest stock price
    try:
        # Attempt to get the dividend rate from the info property
        dividend_rate = stock.info['dividendRate']
    except KeyError:
        # If dividendRate is not available, set it to 0
        dividend_rate = 0
    return price, dividend_rate

latest_price, latest_dividend = get_stock_data(ticker_input)
st.write(f"Current Price for {ticker_input}: ${latest_price}")
st.write(f"Annual Dividend Payment per Share for {ticker_input}: ${latest_dividend}")

# Financial calculations input
average_cost_per_share = st.number_input("Average Cost Per Share", value=13.13)
quantity = st.number_input("Quantity", value=76)

# Calculations
if isinstance(latest_price, (int, float)) and isinstance(average_cost_per_share, (int, float)):
    cost_value = average_cost_per_share * quantity
    market_value = latest_price * quantity
    profit_loss = market_value - cost_value

    st.write(f"Cost Value: ${cost_value:,.2f}")
    st.write(f"Market Value: ${market_value:,.2f}")
    st.write(f"Profit (Loss): ${profit_loss:,.2f}")

    if profit_loss < 0 and isinstance(latest_dividend, (int, float)) and latest_dividend > 0:
        total_annual_dividend = latest_dividend * quantity
        quarterly_dividend = total_annual_dividend / 4  # Assuming dividends are paid quarterly
        monthly_dividend = total_annual_dividend / 12  # Assuming dividends could be divided monthly
        quarters_to_recovery = abs(profit_loss) / quarterly_dividend
        months_to_recovery = abs(profit_loss) / monthly_dividend
        st.write(f"Total Annual Dividend: ${total_annual_dividend:,.2f}")
        st.write(f"Quarters to Recovery: {round(quarters_to_recovery, 2)} quarters")
        st.write(f"Months to Recovery: {round(months_to_recovery, 2)} months")
    elif profit_loss >= 0:
        st.write("Congrats, you are in profit!")
    else:
        st.write("Dividend data not available or dividend is zero, cannot calculate quarters or months to recovery.")
else:
    st.write("Missing or invalid data, cannot perform financial calculations.")
