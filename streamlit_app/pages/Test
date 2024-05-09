import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
from statsmodels.tsa.arima.model import ARIMA
from pmdarima import auto_arima
from statsmodels.tsa.stattools import adfuller
from pmdarima.arima.utils import ndiffs

# Title
st.title('Stock Data Analysis')

# User inputs
ticker = st.text_input('Enter the stock ticker, e.g., ABR:', 'ABR')
start_date = st.text_input('Start date in YYYY-MM-DD format:', '2018-10-19')

# Fetching data
data = yf.download(ticker, start=start_date)
st.write(f"Displaying data for {ticker} from {start_date}:")
st.dataframe(data.tail())

# Plotting
fig, ax = plt.subplots(2, 1, figsize=(12, 8))
ax[0].plot(data['Close'], label='Close Price')
ax[0].set_title('Close Price')
ax[1].bar(data.index, data['Volume'], width=1)
ax[1].set_title('Volume Traded')
st.pyplot(fig)

# ADF test
result = adfuller(data['Close'].dropna())
st.write("ADF Statistic:", result[0])
st.write("p-value:", result[1])

# ARIMA Modeling (optional detailed analysis)
st.write("Running ARIMA model...")
model = auto_arima(data['Close'], suppress_warnings=True, stepwise=True)
st.write("Best ARIMA Model:")
st.write(model.summary())

# Ensure you install all required libraries in your environment
# You may need to handle exceptions or missing data scenarios
