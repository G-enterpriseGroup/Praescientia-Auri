import streamlit as st
import yfinance as yf

# Function to fetch stock price and dividend yield
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    data = stock.history(period="1d")
    price = data['Close'].iloc[0]
    dividend_yield = stock.info.get('dividendYield', 0) * price
    return price, dividend_yield

# Streamlit UI
st.title('Stock Information and Analysis')

# User input for stock ticker

ticker = st.text_input('Enter the stock ticker:', 'AAPL').upper()

# Fetch stock data
price, dividend_yield = get_stock_data(ticker)
st.write(f"Current price of {ticker}: ${price:.2f}")
st.write(f"Annual dividend payment per share: ${dividend_yield:.2f}")

# User inputs for average cost and quantity
avg_cost = st.number_input('Enter your average cost per share:', value=0.0, step=0.01)
quantity = st.number_input('Enter the quantity of stocks owned:', value=0, step=1)

# Calculations
total_investment = avg_cost * quantity
current_value = price * quantity
loss = total_investment - current_value if total_investment > current_value else 0

st.write(f"Total investment: ${total_investment:.2f}")
st.write(f"Current market value: ${current_value:.2f}")
st.write(f"Loss: ${loss:.2f}")

# Calculate dividends and recovery
if loss > 0:
    dividends_per_year = dividend_yield * quantity
    payments_to_recover = loss / dividends_per_year if dividends_per_year else float('inf')
    st.write(f"Dividends per year: ${dividends_per_year:.2f}")
    st.write(f"Number of dividend payments to recover loss: {payments_to_recover:.2f}")
else:
    st.write("No loss to recover.")
