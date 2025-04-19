import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX
import plotly.graph_objects as go
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay, BDay

# ─── Streamlit Config & Branding ────────────────────────────────────────────────
st.set_page_config(layout="wide")
st.markdown("""
    <style>
        #MainMenu, header, footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)
st.write("# Forecasting Stock – Designed & Implemented by Raj Ghotra")

# ─── Helpers ─────────────────────────────────────────────────────────────────────
@st.cache_data
def fetch_history(ticker):
    return yf.Ticker(ticker).history(period="max")

@st.cache_data
def fetch_data(ticker, start, end):
    return yf.download(ticker, start=start, end=end)

def calculate_date(days):
    d = datetime.today()
    cnt = 0
    while cnt < days:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            cnt += 1
    return d

def select_best_order(y, seasonality, p_max=2, d_max=1, q_max=2):
    import warnings
    warnings.filterwarnings("ignore")
    best_aic = np.inf
    best_order = (1,1,1)
    best_seasonal = (1,1,1, seasonality)
    for p in range(p_max+1):
        for d in range(d_max+1):
            for q in range(q_max+1):
                try:
                    mod = SARIMAX(y, order=(p,d,q), seasonal_order=(p,d,q,seasonality))
                    res = mod.fit(disp=False)
                    if res.aic < best_aic:
                        best_aic = res.aic
                        best_order = (p,d,q)
                        best_seasonal = (p,d,q,seasonality)
                except Exception:
                    continue
    return best_order, best_seasonal

# ─── SARIMAX Forecast Section ────────────────────────────────────────────────────
st.sidebar.header("SARIMAX Settings")
SN = st.sidebar.slider("Seasonality (days)", 7, 30, 22)
Ticker = st.sidebar.text_input("Ticker", value="SPY").upper()
start_date = st.sidebar.date_input("Start Date", value=calculate_date(395))
end_date   = st.sidebar.date_input("End Date",   value=calculate_date(30))

st.write(f"**Forecasting {Ticker}**  |  Seasonality: {SN}  |  Period: {start_date} → {end_date}")

if st.button("Run SARIMAX Model"):
    with st.spinner("Running SARIMAX… this may take a few minutes"):
        progress = st.progress(0)
        # load history
        df = fetch_history(Ticker)
        progress.progress(10)

        # ensure index datetime and tz-aware in UTC
        df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df = df.tz_localize('UTC')
        df = df.tz_convert('America/New_York')

        # slice and select close
        start_ts = pd.Timestamp(start_date).tz_localize('America/New_York')
        end_ts   = pd.Timestamp(end_date).tz_localize('America/New_York')
        df = df.loc[start_ts:end_ts][['Close']]
        progress.progress(30)

        C = df['Close'].dropna()
        order, seas = select_best_order(C, SN)
        progress.progress(60)

        model = SARIMAX(C, order=order, seasonal_order=seas).fit(disp=False)
        progress.progress(80)

        cal = USFederalHolidayCalendar()
        hols = cal.holidays(start=df.index[-1], end=df.index[-1] + pd.DateOffset(days=90))
        future_bdays = pd.bdate_range(start=df.index[-1], periods=SN + len(hols), freq='B')
        future = future_bdays.difference(hols)[:SN]

        preds = model.predict(start=len(C), end=len(C) + len(future) - 1)
        future_idx = pd.date_range(future[0], periods=len(preds), freq=CustomBusinessDay(calendar=USFederalHolidayCalendar()))
        preds.index = future_idx
        progress.progress(100)

        # plot actual vs forecast
        fig1, ax = plt.subplots(figsize=(10,5))
        ax.plot(df.index, df['Close'], label='Actual')
        ax.plot(preds.index, preds, '--', label='Forecast')
        ax.set(title=f'{Ticker} Forecast', xlabel='Date', ylabel='Price')
        ax.legend()
        st.pyplot(fig1)
        st.write(pd.DataFrame(preds, columns=['Forecasted Price']))

# ─── Candlestick Chart Section ──────────────────────────────────────────────────
st.title('30-Day Candlestick Chart')
symbol = st.text_input('Enter Stock Ticker for Candles:', value=Ticker).upper()
end_dt = datetime.today()
start_dt = end_dt - timedelta(days=43)

data = fetch_data(symbol, start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))

if not data.empty:
    fig2 = go.Figure(data=[go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close']
    )])
    fig2.update_layout(
        title=f'{symbol} Candlestick (last 30 biz days)',
        xaxis_rangeslider_visible=False,
        xaxis=dict(tickmode='array', tickvals=data.index[::3],
                   ticktext=[d.strftime('%Y-%m-%d') for d in data.index][::3]),
        autosize=False, width=900, height=500
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.write('No data for that ticker.')

# ─── Date Metrics Section ───────────────────────────────────────────────────────
def get_date_metrics():
    today = datetime.now()
    return {
        '30 Biz Days Ago': (today - BDay(30)).strftime('%Y-%m-%d'),
        'QTD Start': datetime(today.year, 3*((today.month-1)//3)+1, 1).strftime('%Y-%m-%d'),
        'YTD Start': datetime(today.year, 1, 1).strftime('%Y-%m-%d'),
        'MTD Start': datetime(today.year, today.month, 1).strftime('%Y-%m-%d'),
        '1 Year Ago': (today - BDay(365)).strftime('%Y-%m-%d'),
        '2 Years Ago': (today - BDay(365*2)).strftime('%Y-%m-%d'),
        '3 Years Ago': (today - BDay(365*3)).strftime('%Y-%m-%d'),
    }

st.title('Date Calculations')
for name, val in get_date_metrics().items():
    st.subheader(name)
    st.text(val)
