if not data.empty:
    # Validate required columns
    required_columns = ['High', 'Low', 'Close']
    if all(col in data.columns for col in required_columns):
        # Drop rows with NaN in required columns
        data.dropna(subset=required_columns, inplace=True)
        
        if not data.empty:
            # Proceed with calculations
            current_price = data['Close'].iloc[-1]
            latest_atr = calculate_atr(data)
            last_14_day_low = data['Low'].tail(14).min()
            stop_loss = last_14_day_low - latest_atr
            percent_difference = ((last_14_day_low - stop_loss) / last_14_day_low) * 100
            
            st.write(f"Current Stock Price: {current_price:.2f}")
            st.write(f"Latest ATR: {latest_atr:.2f}")
            st.write(f"Lowest Low of Last 14 Days: {last_14_day_low:.2f}")
            st.write(f"Stop Loss: {stop_loss:.2f}")
            st.write(f"Percentage Difference: {percent_difference:.2f}%")
        else:
            st.write("Insufficient data after removing invalid rows.")
    else:
        st.write("Data for the entered ticker is missing required columns.")
else:
    st.write("No data found. Please enter a valid ticker symbol.")
