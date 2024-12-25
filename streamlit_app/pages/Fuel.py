import streamlit as st

def calculate_fuel_cost(distance, mpg, gas_price):
    gallons_used = distance / mpg
    fuel_cost = gallons_used * gas_price
    return round(fuel_cost, 2), gallons_used

def calculate_wear_and_tear(distance, rate_per_mile):
    wear_tear_cost = distance * rate_per_mile
    return round(wear_tear_cost, 2)

def calculate_red_light_cost(num_stops, idle_time_per_stop, gas_price):
    fuel_consumption_per_hour = 0.3  # Average fuel consumption while idling in gallons/hour
    fuel_consumed_per_stop = (fuel_consumption_per_hour / 60) * idle_time_per_stop  # Fuel consumed per stop in gallons
    cost_per_stop = fuel_consumed_per_stop * gas_price
    total_red_light_cost = num_stops * cost_per_stop
    return round(total_red_light_cost, 2), round(fuel_consumed_per_stop, 4)

def main():
    st.title("Fuel, Wear & Tear, and Red Light Cost Calculator")

    # User Inputs
    distance = st.number_input("Enter the total round-trip distance (in miles):", min_value=0.0, step=0.1, format="%.1f")
    mpg = st.number_input("Enter your vehicle's fuel efficiency (in MPG):", min_value=0.1, step=0.1, format="%.1f")
    gas_price = st.number_input("Enter the current gas price (per gallon):", min_value=0.0, step=0.01, format="%.2f")
    wear_tear_rate = st.number_input("Enter the wear and tear rate (e.g., IRS rate per mile):", value=0.655, min_value=0.0, step=0.001, format="%.3f")
    num_stops = st.number_input("Enter the number of red lights/stops during the trip:", min_value=0, step=1)
    idle_time_per_stop = st.number_input("Enter the average idle time per stop (in minutes):", min_value=0.0, step=0.1, format="%.1f")

    # Calculate costs
    if st.button("Calculate Costs"):
        if mpg > 0 and distance > 0 and gas_price > 0:
            fuel_cost, gallons_used = calculate_fuel_cost(distance, mpg, gas_price)
            wear_tear_cost = calculate_wear_and_tear(distance, wear_tear_rate)
            red_light_cost, fuel_consumed_per_stop = calculate_red_light_cost(num_stops, idle_time_per_stop, gas_price)

            st.subheader("Results:")
            st.write(f"**Fuel Cost:** ${fuel_cost}")
            st.write(f"- Distance: {distance} miles")
            st.write(f"- Fuel Efficiency: {mpg} MPG")
            st.write(f"- Gallons Used: {round(gallons_used, 4)} gallons")

            st.write(f"**Wear and Tear Cost:** ${wear_tear_cost}")
            st.write(f"- Distance: {distance} miles")
            st.write(f"- Rate per Mile: ${wear_tear_rate}")

            st.write(f"**Red Light Cost:** ${red_light_cost}")
            st.write(f"- Number of Stops: {num_stops}")
            st.write(f"- Idle Time per Stop: {idle_time_per_stop} minutes")
            st.write(f"- Fuel Consumed per Stop: {fuel_consumed_per_stop} gallons")

            st.write(f"**Total Cost:** ${round(fuel_cost + wear_tear_cost + red_light_cost, 2)}")
        else:
            st.error("Please ensure all inputs are greater than zero.")

if __name__ == "__main__":
    main()
