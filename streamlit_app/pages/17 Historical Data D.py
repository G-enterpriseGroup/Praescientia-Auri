# Ensure columns exist and are properly named
required_columns = {'High', 'Low', 'Close'}
if not required_columns.issubset(data.columns):
    st.error(f"The dataset is missing required columns: {required_columns - set(data.columns)}")
else:
    # Handle missing data
    data.dropna(subset=['High', 'Low', 'Close'], inplace=True)

    # Calculate trailing stop percentage
    data['Daily_Range_Percent'] = (
        (data['High'] - data['Low']) / data['Low']
    ) * 100
    average_range_percent = data['Daily_Range_Percent'].mean()
    std_dev_range_percent = data['Daily_Range_Percent'].std()
    optimal_trailing_stop = average_range_percent + std_dev_range_percent

    # Calculate trailing stop value
    max_close_price = data['Close'].max()
    trailing_stop_value = max_close_price * (1 - optimal_trailing_stop / 100)

    # Display results
    st.subheader("Trailing Stop Calculation")
    st.write(f"**Average Daily Range (%):** {average_range_percent:.2f}%")
    st.write(f"**Standard Deviation (%):** {std_dev_range_percent:.2f}%")
    st.write(
        f"**Optimal Trailing Stop (%):** {optimal_trailing_stop:.2f}%"
    )
    st.write(f"**Trailing Stop Value:** ${trailing_stop_value:.2f}")

    # Visualize data
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(data['Close'], label="Close Price", color="blue")
    ax.axhline(
        y=trailing_stop_value,
        color="red",
        linestyle="--",
        label=f"Trailing Stop (${trailing_stop_value:.2f})"
    )
    ax.set_title(f"{ticker} Stock Price with Trailing Stop")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend()
    st.pyplot(fig)
