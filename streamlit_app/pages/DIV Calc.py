import streamlit as st

# Title
st.title('Investment Recovery Calculator')

# User inputs
shares_owned = st.number_input('Number of Shares Owned:', value=76)
average_cost = st.number_input('Average Cost per Share ($):', value=13.13)
dividend_per_share = st.number_input('Dividend per Share per Quarter ($):', value=0.43)

# Calculation
total_investment = shares_owned * average_cost
dividend_per_quarter = dividend_per_share * shares_owned
quarters_needed = total_investment / dividend_per_quarter
years_needed = quarters_needed / 4

# Display results
if st.button('Calculate Recovery Time'):
    st.write(f'Quarters Needed: {quarters_needed:.2f}')
    st.write(f'Years Needed: {years_needed:.2f}')