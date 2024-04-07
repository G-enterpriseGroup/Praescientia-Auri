import streamlit as st

def calculate_chemicals(free_chlorine, total_chlorine, combined_chlorine, ph, alkalinity, cyanuric_acid, pool_volume):
    recommendations = {}

    # Calculate combined chlorine adjustment
    if combined_chlorine > 0.5:
        target_free_chlorine = 10 * combined_chlorine
        chlorine_to_add = target_free_chlorine - free_chlorine
        pounds_calcium_hypochlorite = chlorine_to_add * (pool_volume / 10000) * 0.625 # Approximation
        recommendations['Calcium Hypochlorite (pounds)'] = max(0, round(pounds_calcium_hypochlorite, 2))
    
    # Calculate pH adjustment
    if ph < 7.2:
        ph_increase_needed = 7.4 - ph # Target pH is 7.4
        soda_ash_needed = ph_increase_needed * (pool_volume / 10000) * 2.1 # Approximation
        recommendations['Soda Ash (pounds)'] = round(soda_ash_needed, 2)
    
    # Calculate alkalinity adjustment
    if alkalinity > 120:
        alkalinity_decrease_needed = alkalinity - 120
        muriatic_acid_needed = alkalinity_decrease_needed * (pool_volume / 10000) * 0.8 # Approximation
        recommendations['Muriatic Acid (gallons)'] = round(muriatic_acid_needed, 2)

    return recommendations

# Streamlit UI
st.title('Pool Chemistry Calculator')

with st.form("pool_chemistry_form"):
    st.write("Enter your pool's current chemistry readings and volume:")
    
    free_chlorine = st.number_input('Free Chlorine (ppm)', value=2.97)
    total_chlorine = st.number_input('Total Chlorine (ppm)', value=4.64)
    combined_chlorine = st.number_input('Combined Chlorine (ppm)', value=1.67)
    ph = st.number_input('pH', value=7.1)
    alkalinity = st.number_input('Alkalinity (ppm)', value=195)
    cyanuric_acid = st.number_input('Cyanuric Acid (ppm)', value=41)
    pool_volume = st.number_input('Pool Volume (Gallons)', value=39000, step=1000)
    
    submitted = st.form_submit_button("Calculate Adjustments")
    if submitted:
        recommendations = calculate_chemicals(free_chlorine, total_chlorine, combined_chlorine, ph, alkalinity, cyanuric_acid, pool_volume)
        
        if recommendations:
            st.subheader('Chemical Adjustments Needed:')
            for chemical, amount in recommendations.items():
                st.write(f"{chemical}: {amount}")
        else:
            st.write("Your pool chemistry is within the ideal ranges. No adjustments needed.")

