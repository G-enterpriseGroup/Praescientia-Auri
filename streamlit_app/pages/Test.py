=import streamlit as st
import yfinance as yf
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib.pyplot as plt
from pmdarima import auto_arima

# Function to download stock data
def download_data(stock, start_date, end_date):
    data = yf.download(stock, start=start_date, end=end_date)
    return data

# Function to find best SARIMA model
def fit_sarima(series):
    model = auto_arima(series, seasonal=True, m=5, stepwise=True, suppress_warnings=True, 
                       error_action='ignore', max_order=None, trace=False)
    return model

# Function to forecast the data
def forecast_data(model, periods):
    fitted_model = SARIMAX(model, order=model.order, seasonal_order=model.seasonal_order).fit(disp=False)
    forecast = fitted_model.get_forecast(steps=periods)
    return forecast.conf_int(), forecast.predicted_mean

# Function to plot forecasts
def plot_forecast(actual, forecast, conf_int, title):
    plt.figure(figsize=(10, 5))
    plt.plot(actual, label='Actual')
    plt.plot(forecast.index, forecast, color='red', label='Forecast')
    plt.fill_between(forecast.index, conf_int.iloc[:, 0], conf_int.iloc[:, 1], color='pink', alpha=0.3)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    return plt

# Main function to run the app
def main():
    st.title('Stock Forecast App')

    stock = st.text_input('Enter Stock Symbol', 'AAPL')
    start_date = st.date_input('Start Date', pd.to_datetime('2020-01-01'))
    end_date = st.date_input('End Date', pd.to_datetime('2023-01-01'))

    if st.button('Forecast Stock'):
        data = download_data(stock, start_date, end_date)
        if not data.empty:
            future_dates = pd.date_range(start=data.index.max(), periods=31, freq='B')[1:]
            for column in ['Open', 'High', 'Low', 'Close']:
                st.subheader(f'{column} Price Forecast')
                model = fit_sarima(data[column])
                conf_int, forecast = forecast_data(model, 30)
                forecast = pd.Series(forecast, index=future_dates)
                conf_int = pd.DataFrame(conf_int, index=future_dates)
                fig = plot_forecast(data[column], forecast, conf_int, f'{stock} - {column}')
                st.pyplot(fig)
                forecast.columns = [f'{column} Forecast']
                st.dataframe(forecast)

if __name__ == '__main__':
    main()