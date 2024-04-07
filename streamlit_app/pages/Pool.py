import streamlit as st

# Pool Size Volume
POOL_VOLUME_GALLONS = 39000

def calculate_chemicals(ph, alkalinity, cyanuric_acid, pool_volume):
    chemicals_needed = {}
    # pH Adjustment
    if ph < 6.5:
        ph_up_oz = 20 * (pool_volume / 10000)
    elif 6.5 <= ph <= 6.7:
        ph_up_oz = 16 * (pool_volume / 10000)
    elif 6.8 <= ph <= 7.1:
        ph_up_oz = 12 * (pool_volume / 10000)
    else:
        ph_up_oz = 0
    chemicals_needed['ph_up_oz'] = ph_up_oz
    
    # Alkalinity Adjustment
    alkalinity_adjustment = max(0, 120 - alkalinity) / 10 * 1.5 * (pool_volume / 10000)  # Example calculation
    chemicals_needed['sodium_bisulfate_oz'] = alkalinity_adjustment * 16  # Convert pounds to ounces
    
    # Cyanuric Acid Adjustment
    cyanuric_acid_adjustment = max(0, 50 - cyanuric_acid) / 10 * 13 * (pool_volume / 10000)  # Example calculation
    chemicals_needed['cyanuric_acid_oz'] = cyanuric_acid_adjustment * 16  # Convert pounds to ounces
    
    return chemicals_needed

st.title('Pool Maintenance Helper')

with st.form("pool_chemistry"):
    ph = st.slider('pH Level', 6.0, 8.0, 7.1)
    alkalinity = st.slider('Alkalinity (ppm)', 0, 300, 195)
    cyanuric_acid = st.slider('Cyanuric Acid (ppm)', 0, 100, 41)
    pool_volume = st.slider('Pool Volume (Gallons)', 10000, 50000, 39000)
    
    submitted = st.form_submit_button("Calculate")
    if submitted:
        chemicals_needed = calculate_chemicals(ph, alkalinity, cyanuric_acid, pool_volume)
        st.write(f"Chemicals needed to adjust pH: {chemicals_needed['ph_up_oz']:.2f} ounces")
        st.write(f"Chemicals needed to adjust Alkalinity: {chemicals_needed['sodium_bisulfate_oz']:.2f} ounces")
        st.write(f"Chemicals needed for Cyanuric Acid: {chemicals_needed['cyanuric_acid_oz']:.2f} ounces")

