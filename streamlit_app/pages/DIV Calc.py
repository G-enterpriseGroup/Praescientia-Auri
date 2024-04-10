import streamlit as st
import pandas as pd
import numpy as np

# Title and setup
st.title('Investment Recovery Calculator with Visuals')

# Inputs
shares_owned = st.number_input('Number of Shares Owned:', min_value=0, value=76, step=1)
average_cost = st.number_input('Average Cost per Share ($):', min_value=0.0, value=13.13)
dividend_per_share = st.number_input('Dividend per Share per Quarter ($):', min_value=0.0, value=0.43)
loss_percentage = st.slider('Loss Percentage (%):', min_value=0.0, max_value=100.0, value=100.0)

# Calculations
total_investment = shares_owned * average_cost
loss_value = total_investment * (loss_percentage / 100)
remaining_investment = total_investment - loss_value
dividend_per_quarter = dividend_per_share * shares_owned
quarters_needed = np.inf if dividend_per_quarter <= 0 else remaining_investment / dividend_per_quarter
years_needed = "Infinity" if quarters_needed == np.inf else quarters_needed / 4

# Break-even without dividends
break_even_price = total_investment / shares_owned if shares_owned else 0

# Display calculations
st.write(f'Total Investment Value: ${total_investment:.2f}')
st.write(f'Loss Value: ${loss_value:.2f}')
st.write(f'Remaining Investment Value: ${remaining_investment:.2f}')
st.write(f'Years Needed to Recover (via Dividends): {quarters_needed if quarters_needed != np.inf else "Infinity"}')
st.write(f'Break-even Price per Share: ${break_even_price:.2f}')

# Graph
if st.button('Show Recovery Graph'):
    if quarters_needed != np.inf:
        quarters = np.arange(0, int(np.ceil(quarters_needed)) + 1, 1)
        recovery_values = np.minimum(dividend_per_quarter * quarters, remaining_investment)
    else:
        quarters = np.array([0, 1])
        recovery_values = np.array([0, 0])

    df = pd.DataFrame({
        'Quarter': quarters,
        'Recovery Value ($)': recovery_values
    })

    st.line_chart(df.set_index('Quarter'))

# Instructions
st.write('Adjust the loss percentage to see its effect on recovery time. The tool provides recovery estimations through dividends and the break-even share price.')