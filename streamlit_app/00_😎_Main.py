import streamlit as st

st.set_page_config(
    page_title="Stock Prediction App",
    page_icon="😎",
)
import streamlit as st

# Your LinkedIn profile URL
linkedin_url = "https://www.linkedin.com/in/balraj-s-ba0b32108"

# Using st.markdown to create a clickable link with custom text
st.markdown(f'<a href="{linkedin_url}" target="_blank" style="font-size: 32px;">LinkedIn</a>', unsafe_allow_html=True)
st.markdown(
    """# 📈 **Equitrend**
### **Predicting Stocks with Equitrend**

**Equitrend is an Quantitative Algorithmic-powered stock price prediction app built with Python and Streamlit. It utilizes machine learning models to forecast stock prices and help investors make data-driven decisions.**

Hello, my name is Raj. As of 2024, at 24 years of age, I am launching my company. My engagement with finance began at 17 in 2017. At that time, my career path was not clear, but I aimed to generate wealth and create a lasting impact. I opted against purchasing stock trading courses, questioning their value and the intentions of their sellers. Instead, I chose self-education, relying on the internet for articles and books on candlestick charts, price actions, and trend analysis to develop my trading skills.

My technical skills development started at 13 in 2013, through coding and jailbreaking iPods and iPads using software like Greenp0isen and BlackRa1n. I sold these devices on eBay for profit, gaining early experience in market dynamics. This period also marked the introduction of Bitcoin, signaling a new era in cryptography and algorithms. My transition from technology and trading to founding my company reflects a commitment to leveraging financial knowledge and market insights to establish a durable and influential presence in the investment world.

## 🏗️ **How It's Built**

Equitrend is built with these core frameworks and modules:

- **Streamlit** - To create the web app UI and interactivity 
- **YFinance** - To fetch financial data from Yahoo Finance API

The app workflow is:

1. User selects a stock ticker
2. Historical data is fetched with YFinance
3. ARIMA model is trained on the data 
4. Model makes multi-day price forecasts
5. Results are plotted with Plotly

## 🎯 **Key Features**

- **Real-time data** - Fetch latest prices and fundamentals 
- **Financial charts** - Interactive historical and forecast charts
- **ARIMA forecasting** - Make statistically robust predictions
- **Backtesting** - Evaluate model performance
- **Responsive design** - Works on all devices


## **⚖️ Disclaimer**
**This is not financial advice! Use forecast data to inform your own investment research. No guarantee of trading performance.**
"""
)
