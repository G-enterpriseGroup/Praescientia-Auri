import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.title('Covered Call Calculator')

# Input section for underlying stock
st.header('Underlying stock')
symbol = st.text_input('Symbol', 'PULS')
price = st.number_input('Price', value=49.75, step=0.01)
quantity = st.number_input('Quantity', value=100, step=1)
dividend = st.number_input('Dividend', value=0.0, step=0.01)
ex_date = st.date_input('Ex-date', value=pd.to_datetime('2024-06-01'))
called_away = st.date_input('Called away date', value=pd.to_datetime('2024-06-01'))

# Input section for option
st.header('Option')
option_type = st.selectbox('Buy/sell', ['Sell', 'Buy'])
strike_price = st.number_input('Strike Price', value=50.0, step=0.01)
expiry_date = st.date_input('Expiry Date', value=pd.to_datetime('2024-06-21'))
premium = st.number_input('Premium (per share)', value=1.35, step=0.01)
quantity_option = st.number_input('Quantity (contracts)', value=1, step=1)

# Calculations
leg_cost = premium * quantity_option * 100
initial_premium = leg_cost if option_type == 'Sell' else -leg_cost
max_return = (strike_price - price) * quantity * 100 if option_type == 'Sell' else (price - strike_price) * quantity * 100
max_risk = (price * quantity * 100) - initial_premium
breakeven = price - (premium if option_type == 'Sell' else -premium)
days_until_expiry = (expiry_date - datetime.now().date()).days
annualized_return = (max_return / initial_premium) * (365 / days_until_expiry) if initial_premium != 0 else 0

# Display results
st.header('Estimates')
st.write(f"Initial premium: ${initial_premium:.2f}")
st.write(f"Max return: ${max_return:.2f}")
st.write(f"Max risk: ${max_risk:.2f}")
st.write(f"B/E at expiry: ${breakeven:.2f}")
st.write(f"Days Until Expiry: {days_until_expiry} days")
st.write(f"Annualized Return: {annualized_return:.2f}%")

# Create the matrix (simplified for this example)
matrix_data = {
    'Stock Price Range': np.arange(price - 5, price + 5, 0.25),
    'P/L': [max_return if x >= strike_price else (x - price) * quantity * 100 for x in np.arange(price - 5, price + 5, 0.25)]
}
matrix_df = pd.DataFrame(matrix_data)

st.header('Matrix Values')
st.dataframe(matrix_df)
