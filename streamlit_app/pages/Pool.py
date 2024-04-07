import streamlit as st

# Constants
POOL_VOLUME_GALLONS = 38000
PH_ADJUSTMENT_RATES = {
    '6.8-7.1': 12,
    '6.5-6.7': 16,
    'below 6.5': 20
}
SODIUM_BISULFATE_PCT = 0.932
SODIUM_CARBONATE_PCT = 1.0
LIQUID_CHLORINE_PCT = 0.1

def calculate_ph_up_amount(current_ph, pool_volume):
    for ph_range, ounces_per_10000 in PH_ADJUSTMENT_RATES.items():
        if current_ph <= float(ph_range.split('-')[1]):
            return ounces_per_10000 * (pool_volume / 10000)
    return 0

def calculate_chemicals(ph, alkalinity, pool_volume):
    ph_up_amount = calculate_ph_up_amount(ph, pool_volume)
    # Assuming a fixed ratio for simplicity; adjust based on specific needs
    sodium_bisulfate_amount = (alkalinity - 120) * pool_volume / 10000 if alkalinity > 120 else 0
    return ph_up_amount, sodium_bisulfate_amount

st.title('Pool Water Adjustment Calculator')

ph = st.slider('Current pH Level', 6.0, 8.0, 7.1)
alkalinity = st.slider('Alkalinity (ppm)', 0, 300, 195)

ph_up_amount, sodium_bisulfate_amount = calculate_chemicals(ph, alkalinity, POOL_VOLUME_GALLONS)

st.write(f'### pH Adjustment')
st.write(f'**Sodium Carbonate Needed**: {ph_up_amount:.2f} ounces')

if sodium_bisulfate_amount > 0:
    st.write(f'### Alkalinity Adjustment')
    st.write(f'**Sodium Bisulfate Needed**: {sodium_bisulfate_amount:.2f} ounces')
else:
    st.write('No adjustment needed for alkalinity.')
