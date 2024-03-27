def calculate_date(days, start=True):
    current_date = datetime.today()
    delta_days = 0
    while delta_days < days:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:
            delta_days += 1
    return current_date
default_start_date = calculate_date(395)
default_end_date = calculate_date(30, start=False)
SN = st.slider('Seasonality', 7, 30, 22)
EMA_values = {f'EMA{i}': st.slider(f'EMA{i}', 0, 100, default) for i, default in zip([12, 26, 9], [13, 39, 9])}
split_percentage = st.slider('Training set proportion %', 0.2, 0.99, 0.80)
Ticker = st.text_input('Ticker', value="SPY")
start_date1 = st.date_input('Start Date', value=default_start_date)
end_date1 = st.date_input('End Date', value=default_end_date)
st.write(f'Days Predicting: 30\nSeasonality: {SN}\n' + '\n'.join([f'{k}: {v}' for k, v in EMA_values.items()]) +
         f'\nTicker: {Ticker}\nStart Date: {start_date1}\nEnd Date: {end_date1}\nTraining set proportion %: {split_percentage}')
if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...Estimated 4 Minutes'):
        progress_bar = st.progress(0)
        df = yf.Ticker(Ticker).history(period="max")
        df = df.loc[pd.to_datetime(start_date1).tz_localize('America/New_York'):pd.to_datetime(end_date1).tz_localize('America/New_York')]
        if df.index.tz is None:
            df.index = pd.to_datetime(df.index).tz_localize('America/New_York')
        else:
            df.index = pd.to_datetime(df.index).tz_convert('America/New_York')
        df = df[['Close']].copy()
        progress_bar.progress(10)
        for ema, value in EMA_values.items():
            df[ema] = df['Close'].ewm(span=value, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        C = df["Close"].dropna()
        progress_bar.progress(30)
        auto_model = auto_arima(C, trace=True, suppress_warnings=True)
        arima_order = auto_model.order
        seasonal_order = (arima_order[0], arima_order[1], arima_order[2], SN)
        model = SARIMAX(C, order=arima_order, seasonal_order=seasonal_order).fit()
        progress_bar.progress(80)
        cal = USFederalHolidayCalendar()
        holidays = cal.holidays(start=df.index.max(), end=df.index.max() + pd.DateOffset(days=90))
        future_dates = pd.bdate_range(start=df.index.max(), periods=30 + len(holidays), freq='B')
        future_dates = future_dates[~future_dates.isin(holidays)][:30]
        predictions = model.predict(start=len(C), end=len(C) + len(future_dates) - 1, dynamic=True)
        # Use a built-in holiday calendar
        custom_business_day = CustomBusinessDay(calendar=USFederalHolidayCalendar())
        
        # Generate the date range
        future_dates_index = pd.date_range(start=future_dates[0], periods=len(predictions), freq=custom_business_day)
        predictions.index = future_dates_index
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['Close'], label='Actual Close')
        plt.plot(predictions.index, predictions, label='Forecast', linestyle='--')
        plt.title(f'{Ticker} Stock Price Forecast')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.tight_layout()
        st.pyplot(plt)
        # Assuming 'predictions' is your forecasted values and 'future_dates_index' are the corresponding future dates
        
        # Create a DataFrame for the forecasted values
        future_df = pd.DataFrame({'Forecasted Price': predictions.values}, index=future_dates_index)
        
        # Display the DataFrame in Streamlit
        st.write(future_df)
        
        # Plotting historical data and future predictions
        plt.figure(figsize=(15, 7))
        plt.plot(future_df.index, future_df['Forecasted Price'], label='Forecasted Price', linestyle='--', color='red')
        plt.title(f'{Ticker} Historical and Forecasted Stock Price')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.tight_layout()
        
        # Show the plot in Streamlit
        st.pyplot(plt)
        
        progress_bar.progress(100)
        st.success("Model run successfully!")
