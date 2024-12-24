import streamlit as st

def calculate_fuel_cost(distance, mpg, gas_price):
    gallons_used = distance / mpg
    fuel_cost = gallons_used * gas_price
    return round(fuel_cost, 2)

def calculate_wear_and_tear(distance, rate_per_mile):
    wear_tear_cost = distance * rate_per_mile
    return round(wear_tear_cost, 2)

def main():
    st.title("Fuel and Wear & Tear Cost Calculator")

    # User Inputs
    distance = st.number_input("Enter the total round-trip distance (in miles):", min_value=0.0, step=0.1, format="%.1f")
    mpg = st.number_input("Enter your vehicle's fuel efficiency (in MPG):", min_value=0.1, step=0.1, format="%.1f")
    gas_price = st.number_input("Enter the current gas price (per gallon):", min_value=0.0, step=0.01, format="%.2f")
    wear_tear_rate = st.number_input("Enter the wear and tear rate (e.g., IRS rate per mile):", value=0.655, min_value=0.0, step=0.001, format="%.3f")

    # Calculate costs
    if st.button("Calculate Costs"):
        if mpg > 0 and distance > 0 and gas_price > 0:
            fuel_cost = calculate_fuel_cost(distance, mpg, gas_price)
            wear_tear_cost = calculate_wear_and_tear(distance, wear_tear_rate)

            st.subheader("Results:")
            st.write(f"**Fuel Cost:** ${fuel_cost}")
            st.write(f"**Wear and Tear Cost:** ${wear_tear_cost}")
            st.write(f"**Total Cost:** ${round(fuel_cost + wear_tear_cost, 2)}")
        else:
            st.error("Please ensure all inputs are greater than zero.")

if __name__ == "__main__":
    main()
