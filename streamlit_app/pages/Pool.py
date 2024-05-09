import streamlit as st

def calculate_total_gallons(flow_rate, rinse_time, backwash_time):
    # Total minutes are the sum of rinse and backwash times
    total_minutes = rinse_time + backwash_time
    # Total gallons are the product of the flow rate and total time
    return flow_rate * total_minutes

def fill_time(total_gallons):
    # Each gallon takes 10 seconds to fill
    total_seconds = total_gallons * 10
    # Convert seconds to hours and minutes
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return hours, minutes

def main():
    st.title('Water Flow Calculation App')

    # Constants
    power_hp = 3  # horsepower
    power_watts = power_hp * 746  # convert horsepower to watts
    density_water = 1000  # kg/m^3 for water
    gravity = 9.81  # m/s^2
    efficiency = 0.75  # assumed efficiency
    head = 20  # meters

    # Calculate flow rate Q in cubic meters per second
    flow_rate_m3_s = power_watts / (head * density_water * gravity * efficiency)

    # Convert flow rate to liters per minute (1 m^3/s = 1000 L/min * 60 s/min)
    flow_rate_liters_per_minute = flow_rate_m3_s * 1000 * 60

    # Convert flow rate from liters per minute to gallons per minute (1 liter = 0.264172 gallons)
    flow_rate_gallons_per_minute = flow_rate_liters_per_minute * 0.264172

    # Sliders for Rinse and Backwash time in minutes
    rinse_time = st.slider('Rinse Time (minutes)', min_value=1, max_value=60, value=3)
    backwash_time = st.slider('Backwash Time (minutes)', min_value=1, max_value=60, value=3)

    # Calculate total gallons used
    total_gallons = calculate_total_gallons(flow_rate_gallons_per_minute, rinse_time, backwash_time)

    # Calculate the time required to fill back the gallons
    hours, minutes = fill_time(total_gallons)

    # Display the total gallons used and the time required to fill them
    st.write(f'Total Gallons Used: {total_gallons:.2f}')
    st.write(f'Time to Fill Back
