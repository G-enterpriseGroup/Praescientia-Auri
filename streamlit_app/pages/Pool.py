import streamlit as st

# Title
st.title('Pool Chemical Dosage Calculator')

# User Inputs
pool_volume = st.number_input('Enter your pool volume (in gallons):', min_value=0.0, format='%f')
desired_change = st.number_input('Enter the desired chemical change (ppm):', min_value=0.0, format='%f')
chemical_label_amount = st.number_input('Enter the amount of chemical from the label (in lbs or oz):', min_value=0.0, format='%f')
given_water_volume = st.number_input('Enter the given water volume from the label (in gallons):', min_value=0.0, format='%f')
given_chemical_change = st.number_input('Enter the given chemical change from the label (ppm):', min_value=0.0, format='%f')

# Calculation
if st.button('Calculate Dosage'):
    pool_factor = pool_volume / given_water_volume
    change_factor = desired_change / given_chemical_change
    chemical_dosage = pool_factor * change_factor * chemical_label_amount
    st.write(f'You need {chemical_dosage:.2f} lbs or oz of the chemical for your pool.')


