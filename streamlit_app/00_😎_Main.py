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
The code imports necessary libraries for data manipulation, visualization, and financial analysis. It acquires historical stock data, processes this data to calculate key financial indicators like moving averages and the MACD, a momentum indicator that shows the relationship between two moving averages of a security's price. The Signal line, a key part of MACD analysis, is also calculated along with a histogram that helps visualize the difference between the MACD and the Signal line.

The financial indicators are plotted over time, allowing the user to assess the historical performance and trends of the stock. The historical data is then used to fit a predictive model, which is designed to forecast future values of these indicators based on past trends and patterns. The forecasting model is adjusted using sliders that control parameters such as seasonality and the smoothing factor of moving averages.

The predictions made by this model can aid in identifying potential future movements in the stock's price, allowing for more informed decision-making in investment strategies. This could be particularly useful for tasks like optimizing entry and exit points in trading, managing portfolio risk, and conducting market analysis. By providing a visual representation of future predictions alongside historical data, the code facilitates a comparative analysis to evaluate the potential accuracy and effectiveness of the predictive model.

# Seasonality "SN"
In this code, seasonality refers to the recurrent fluctuations in stock prices that occur at regular intervals due to patterns in business activity, market sentiment, or other cyclical factors. The seasonality parameter, controlled by a slider, allows the user to specify the periodicity of the seasonal effects within the data—this could represent a typical pattern such as quarterly earnings reports, annual fiscal policies, or holiday shopping seasons, which are known to influence stock behavior.

The user should judiciously set the seasonality parameter based on domain knowledge of the stock's behavior and the broader market. For instance, retail stocks may exhibit strong seasonal patterns around major holidays, while utility stocks might be more affected by seasonal changes in weather. Understanding and correctly setting this parameter can improve the model's predictive accuracy by aligning it more closely with the stock's intrinsic patterns.

# Disclaimer
The forecasting model presented operates strictly on historical quantitative data, and while it systematically analyzes past stock price movements and trends, it does not account for unforeseen events or new information. Such external factors include natural disasters, economic shifts, market sentiment, and significant news events, all of which can substantially impact stock prices. Therefore, while the model can provide insights into potential future stock behavior based on historical patterns, its predictions should not be solely relied upon for investment decisions. Users should consider it as one tool among many and integrate comprehensive market analysis, including qualitative factors, when evaluating investment opportunities.


The app workflow is:

1. User selects a stock ticker
2. Historical data is fetched with YFinance
.4. Model makes multi-day price forecasts
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
