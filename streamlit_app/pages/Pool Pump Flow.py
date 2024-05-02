import streamlit as st

def calculate_flow_rate(power_hp, rpm, density=1000, gravity=9.81):
    # Convert horsepower to watts
    power_watts = power_hp * 746

    # Assume head and efficiency vary with power and rpm; these are estimated for demonstration.
    # These could be refined with more specific data or formulas.
    head = 10 + (rpm / 250)  # Simple assumption that head increases with rpm
    efficiency = 0.7 + (power_hp - 1) * 0.05  # Efficiency increases with horsepower
    
    # Flow rate in cubic meters per second using the power equation
    flow_rate_m3_s = power_watts / (head * density * gravity * efficiency)
    
    # Convert flow rate to gallons per minute (1 m^3/s = 264.172 gallons per minute * 60)
    flow_rate_gallons_per_minute = flow_rate_m3_s * 264.172 * 60
    return flow_rate_gallons_per_minute

st.title('Pump Flow Rate Calculator')

# Sliders for user input
power_hp = st.slider('Horsepower (HP)', min_value=1.0, max_value=3.0, step=0.1, value=3.0)
rpm = st.slider('RPM', min_value=500, max_value=3000, step=100, value=2500)

# Perform calculation
result = calculate_flow_rate(power_hp, rpm)

# Display the result
st.write(f"The estimated flow rate is {result:.2f} gallons per minute.")