# Fetch the stock data
try:
    data = yf.download(ticker, period='1y', interval='1d')
except Exception as e:
    st.write(f"Error fetching data: {e}")
    data = pd.DataFrame()

# Validate the data
if isinstance(data, pd.DataFrame) and not data.empty:
    required_columns = ['High', 'Low', 'Close']
    if all(col in data.columns for col in required_columns):
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
            st.write("No sufficient data after filtering.")
    else:
        st.write("Data is missing required columns.")
else:
    st.write("No data found. Please enter a valid ticker symbol.")
