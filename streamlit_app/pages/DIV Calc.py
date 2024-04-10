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
quarters_needed = remaining_investment / dividend_per_quarter
years_needed = quarters_needed / 4

# Display calculations
st.write(f'Total Investment Value: ${total_investment:.2f}')
st.write(f'Loss Value: ${loss_value:.2f}')
st.write(f'Remaining Investment Value: ${remaining_investment:.2f}')
st.write(f'Quarters Needed to Recover: {quarters_needed:.2f}')
st.write(f'Years Needed to Recover: {years_needed:.2f}')

# Graph
if st.button('Show Recovery Graph'):
    quarters = np.arange(0, int(np.ceil(quarters_needed)) + 1, 1)
    recovery_values = np.minimum(dividend_per_quarter * quarters, remaining_investment)

    df = pd.DataFrame({
        'Quarter': quarters,
        'Recovery Value ($)': recovery_values
    })

    st.line_chart(df.set_index('Quarter'))

# Instructions
st.write('Adjust the loss percentage to see how it affects the recovery time and visualize the recovery process.')