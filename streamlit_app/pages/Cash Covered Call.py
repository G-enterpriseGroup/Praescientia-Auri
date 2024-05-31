import streamlit as st

# Function to calculate covered call profit/loss
def calculate_covered_call(stock_price, strike_price, premium, stock_owned, contract_size=100):
    max_profit = (strike_price - stock_price + premium) * stock_owned
    breakeven_price = stock_price - premium
    stock_loss = stock_price - breakeven_price
    net_profit = premium * stock_owned
    return max_profit, breakeven_price, stock_loss, net_profit

st.title("Covered Call Calculator")

# Input fields
stock_price = st.number_input("Stock Price", min_value=0.0, value=49.72, step=0.01)
strike_price = st.number_input("Strike Price", min_value=0.0, value=50.0, step=0.01)
premium = st.number_input("Premium Received", min_value=0.0, value=4.80, step=0.01)
stock_owned = st.number_input("Number of Shares Owned", min_value=1, value=100, step=1)
contract_size = st.number_input("Contract Size", min_value=1, value=100, step=1)

# Calculate results
max_profit, breakeven_price, stock_loss, net_profit = calculate_covered_call(stock_price, strike_price, premium, stock_owned, contract_size)

# Display results
st.subheader("Results")
st.write(f"Maximum Profit: ${max_profit:.2f}")
st.write(f"Breakeven Price: ${breakeven_price:.2f}")
st.write(f"Stock Loss (if stock price drops to zero): ${stock_loss:.2f}")
st.write(f"Net Profit from Premium: ${net_profit:.2f}")

if __name__ == "__main__":
    st.run()
