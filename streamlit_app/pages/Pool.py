import streamlit as st

# Title of the application
st.title('Pool Chemical Dosage Calculator')

# Input fields for the user to provide necessary data
pool_volume = st.number_input('Enter your pool volume (in gallons):', min_value=0.0, step=1000.0, format='%f')
desired_change = st.number_input('Enter the desired chemical change (in ppm):', min_value=0.0, step=1.0, format='%f')
chemical_label_amount = st.number_input('Enter the amount of chemical from the label (in lbs):', min_value=0.0, step=0.1, format='%f')
given_water_volume = st.number_input('Enter the given water volume from the label (in gallons):', min_value=0.0, step=1000.0, format='%f')
given_chemical_change = st.number_input('Enter the given chemical change from the label (in ppm):', min_value=0.0, step=1.0, format='%f')

# Button to trigger the calculation
if st.button('Calculate Dosage'):
    # Calculation logic
    pool_factor = pool_volume / given_water_volume
    change_factor = desired_change / given_chemical_change
    chemical_dosage = pool_factor * change_factor * chemical_label_amount
    # Display the result
    st.write(f'You need {chemical_dosage:.2f} lbs of the chemical for your pool.')
