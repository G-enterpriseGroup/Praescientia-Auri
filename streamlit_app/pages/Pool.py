import streamlit as st

# Title
st.title('Pool Maintenance Calculator')

# Pump Mode Confirmation
st.markdown('**Pump should be on Mode 2 for 24-hour variable speed.**')

# Chemical Addition Section
st.header('Weekly Chemical Additions')
chlorine_tabs = st.number_input('Chlorine tabs in skimmer (number of tabs)', min_value=0)
bleach_chlorine_gallons = st.number_input('Gallons of pool bleach chlorine added (gallons)', min_value=0.0, format='%f')
algae_killer_oz = st.number_input('Algae killer added (oz)', min_value=0.0, format='%f')
water_clarifier_oz = st.number_input('Water clarifier added (oz)', min_value=0.0, format='%f')

# Chemistry Levels Input
st.header('Current Chemistry Levels')
chlorine_level = st.slider('Chlorine Level', 0.0, 5.0, 1.5)
ph_level = st.slider('pH Level', 6.0, 8.5, 7.5)
total_alkalinity_level = st.number_input('Total Alkalinity Level (ppm)', min_value=0)
stabilizer_level = st.number_input('Stabilizer Level (ppm)', min_value=0)

# Dosage Recommendations Based on pH Levels
st.header('Dosage Recommendations')
if ph_level < 7.8:
    st.write('pH level is within the desired range.')
elif ph_level < 8.4:
    st.write('Add Half Gallon of Muriatic Acid.')
else:
    st.write('Add One Full Gallon of Muriatic Acid.')

# If Alkaline Level adjustments needed
if total_alkalinity_level > 180:
    st.write('Reduce the pH to 7.2 by adding Muriatic Acid.')

# Pool Volume
st.markdown('**Pool Volume:** 35,500 gallons')

# Run the app
if st.button('Calculate'):
    # This is where you would process the inputs and give out the recommendations
    st.write('Chemical adjustments calculated.')

