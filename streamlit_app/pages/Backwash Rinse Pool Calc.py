import streamlit as st

def calculate_flow_rate(power_hp, head, efficiency, density=1000, gravity=9.81):
    power_watts = power_hp * 746  # convert horsepower to watts
    flow_rate_m3_s = power_watts / (head * density * gravity * efficiency)  # m^3/s
    flow_rate_gallons_per_minute = flow_rate_m3_s * 264.172 * 60  # convert to gallons per minute
    return flow_rate_gallons_per_minute

st.title('Pump Flow Rate Calculator')

# Sliders
power_hp = st.slider('Horsepower (HP)', min_value=0.5, max_value=10.0, step=0.1, value=3.0)
head = st.slider('Head (meters)', min_value=1, max_value=100, step=1, value=20)
efficiency = st.slider('Efficiency (as a decimal)', min_value=0.1, max_value=1.0, step=0.05, value=0.75)

# Calculation
result = calculate_flow_rate(power_hp, head, efficiency)

# Display result
st.write(f"The estimated flow rate {result:.2f} gallons per minute.")