
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
import yfinance as yf
import datetime
from datetime import datetime, timedelta
import os, pickle
import streamlit as st

st.set_page_config(layout="wide")

# Function to hide Streamlit branding and sidebar
def hide_streamlit_branding():
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# Set the title of the app
st.write("""
# Forecasting Stock - Designed & Implemented by Raj Ghotra
The code imports necessary libraries for data manipulation, visualization, and financial analysis. It acquires historical stock data, processes this data to calculate key financial indicators like moving averages and the MACD, a momentum indicator that shows the relationship between two moving averages of a security's price. The Signal line, a key part of MACD analysis, is also calculated along with a histogram that helps visualize the difference between the MACD and the Signal line.

The financial indicators are plotted over time, allowing the user to assess the historical performance and trends of the stock. The historical data is then used to fit a predictive model, which is designed to forecast future values of these indicators based on past trends and patterns. The forecasting model is adjusted using sliders that control parameters such as seasonality and the smoothing factor of moving averages.

The predictions made by this model can aid in identifying potential future movements in the stock's price, allowing for more informed decision-making in investment strategies. This could be particularly useful for tasks like optimizing entry and exit points in trading, managing portfolio risk, and conducting market analysis. By providing a visual representation of future predictions alongside historical data, the code facilitates a comparative analysis to evaluate the potential accuracy and effectiveness of the predictive model.

# Seasonality "SN"
In this code, seasonality refers to the recurrent fluctuations in stock prices that occur at regular intervals due to patterns in business activity, market sentiment, or other cyclical factors. The seasonality parameter, controlled by a slider, allows the user to specify the periodicity of the seasonal effects within the data—this could represent a typical pattern such as quarterly earnings reports, annual fiscal policies, or holiday shopping seasons, which are known to influence stock behavior.

The user should judiciously set the seasonality parameter based on domain knowledge of the stock's behavior and the broader market. For instance, retail stocks may exhibit strong seasonal patterns around major holidays, while utility stocks might be more affected by seasonal changes in weather. Understanding and correctly setting this parameter can improve the model's predictive accuracy by aligning it more closely with the stock's intrinsic patterns.

# Disclaimer
The forecasting model presented operates strictly on historical quantitative data, and while it systematically analyzes past stock price movements and trends, it does not account for unforeseen events or new information. Such external factors include natural disasters, economic shifts, market sentiment, and significant news events, all of which can substantially impact stock prices. Therefore, while the model can provide insights into potential future stock behavior based on historical patterns, its predictions should not be solely relied upon for investment decisions. Users should consider it as one tool among many and integrate comprehensive market analysis, including qualitative factors, when evaluating investment opportunities.""")

# Create sliders for each variable
DD = 30
SN = st.slider('Seasonality', min_value=7, max_value=100, value=22)
EMA12 = st.slider('EMA12', min_value=0, max_value=100, value=13)
EMA26 = st.slider('EMA26', min_value=0, max_value=100, value=39)
EMA9 = st.slider('EMA9', min_value=0, max_value=100, value=9)

# Text input for Ticker
Ticker = st.text_input('Ticker', value="DMLP")

# Default to the date one year ago from today
default_start_date = datetime.today() - timedelta(days=365)

start_date1 = st.date_input('Start Date', value=default_start_date)

# Display the current values of the variables
st.write('Days Predicting:', DD)
st.write('Seasonality:', SN)
st.write('EMA12:', EMA12)
st.write('EMA26:', EMA26)
st.write('EMA9:', EMA9)
st.write('Ticker:', Ticker)
st.write('Start Date:', start_date1)

if st.button('Run SARIMAX Model'):
    with st.spinner('Model is running, please wait...Estimated 4 Minutes'):
        progress_bar = st.progress(0)
    
        ### - CHANGE THE TICKER IN THE "" WITH THE STOCK YOU WISH TO VIEW
        df = yf.Ticker(Ticker)
        ### - DO NOT CHANGE THIS, THIS IS SET TO THE MAX TO IMPORT ALL THE HISTORICAL DATA TO LOCATE
        df = df.history(period="max")
        df = df.loc[start_date1:].copy()
        df.index = df.index.strftime('%Y-%m-%d')
        df.index = pd.to_datetime(df.index)
        del df['Open']
        del df['High']
        del df['Low']
        del df['Volume']
        del df['Dividends']
        del df['Stock Splits']
        progress_bar.progress(1)


        # Calculating the 12 EMA
        df['EMA_19'] = df['Close'].ewm(span=EMA12, adjust=False).mean()
        df['EMA_39'] = df['Close'].ewm(span=EMA26, adjust=False).mean()
        df['EMA_9'] = df['Close'].ewm(span=EMA9, adjust=False).mean()
        df['MACD'] = df['EMA_19'] - df['EMA_39']
        # Assuming df['MACD'] is already calculated as shown in your code
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']
        del df['EMA_19']
        del df['EMA_39']
        del df['EMA_9']
        progress_bar.progress(2)


        df

        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import pandas as pd

        # Assuming 'df' is your DataFrame, and its index is of datetime type. If not, you've already converted it.
        # Also assuming 'df' already has 'MACD', 'Signal', and 'Close' columns calculated.

        # Sorting the DataFrame by the index (date) to ensure the data is in chronological order
        df = df.sort_index()
        progress_bar.progress(3)

        # Calculate the Histogram if not already done
        df['Histogram'] = df['MACD'] - df['Signal']

        # Creating a figure and a grid of subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7))

        # Plotting the Close price on ax1
        ax1.plot(df.index, df['Close'], label='Close', color='skyblue')
        ax1.set_title('Close Price')
        ax1.legend(loc='upper left')
        ax1.grid(True)

        # Formatting the date to ensure that the date does not overlap
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=45))
        ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax1.xaxis.get_major_locator()))

        # Plotting MACD and Signal Line on ax2

        ax2.plot(df.index, df['MACD'], label='MACD', color='blue', linewidth=1.5)
        ax2.plot(df.index, df['Signal'], label='Signal Line', color='red', linewidth=1.5)

        # Plotting the Histogram as bar plot on ax2
        ax2.bar(df.index, df['Histogram'], label='Histogram', color='grey', alpha=0.3)

        ax2.set_title('MACD, Signal Line, and Histogram')
        ax2.legend(loc='upper left')
        ax2.grid(True)

        # Formatting the date for the second subplot
        ax2.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=45))
        ax2.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax2.xaxis.get_major_locator()))

        ax2.set_xlabel('Date')
        ax2.set_ylabel('Value')

        # Adjusting layout
        plt.tight_layout()

        # Show the plot
        plt.show()

        C = df["Close"].dropna().tolist()
        M = df["MACD"].dropna().tolist()
        S = df["Signal"].dropna().tolist()
        H = df["Histogram"].dropna().tolist()
        progress_bar.progress(4)

        from statsmodels.tsa.arima.model import ARIMA
        from pmdarima import auto_arima
        progress_bar.progress(5)

        split_percentage = 0.80  # % for training
        split_index = int(len(H) * split_percentage)
        progress_bar.progress(6)

        H_train = M[:split_index]
        H_test = M[split_index:]
        print(len(H_train), len(H_test))
        progress_bar.progress(7)

        split_percentage = 0.80  # % for training
        split_index = int(len(C) * split_percentage)
        progress_bar.progress(8)

        C_train = M[:split_index]
        C_test = M[split_index:]
        print(len(C_train), len(C_test))
        progress_bar.progress(9)

        split_percentage = 0.80  # % for training
        split_index = int(len(M) * split_percentage)
        progress_bar.progress(10)

        M_train = M[:split_index]
        M_test = M[split_index:]
        print(len(M_train), len(M_test))
        progress_bar.progress(11)

        split_percentage = 0.80  # % for training
        split_index = int(len(S) * split_percentage)
        progress_bar.progress(12)

        S_train = S[:split_index]
        S_test = S[split_index:]
        print(len(S_train), len(S_test))
        progress_bar.progress(13)

        stepwise_fit = auto_arima(H,trace=True,suppress_warnings=True)
        stepwise_fit
        progress_bar.progress(14)

        def extract_best_arima_order(stepwise_fit):
            # Search for the line starting with "Best model:"
            for line in stepwise_fit.split('\n'):
                if line.startswith("Best model:"):
                    # Extract numbers within parentheses
                    order = tuple(map(int, line.split('ARIMA')[1].split('(')[1].split(')')[0].split(',')))
                    return order
            return None
        arima_order = stepwise_fit.order
        arima_order
        hp, hd, hq = arima_order
        progress_bar.progress(15)

        stepwise_fit = auto_arima(C,trace=True,suppress_warnings=True)
        stepwise_fit
        progress_bar.progress(16)

        def extract_best_arima_order(stepwise_fit):
            # Search for the line starting with "Best model:"
            for line in stepwise_fit.split('\n'):
                if line.startswith("Best model:"):
                    # Extract numbers within parentheses
                    order = tuple(map(int, line.split('ARIMA')[1].split('(')[1].split(')')[0].split(',')))
                    return order
            return None
        arima_order = stepwise_fit.order
        arima_order
        cp, cd, cq = arima_order
        progress_bar.progress(17)
        
        stepwise_fit = auto_arima(M,trace=True,suppress_warnings=True)
        stepwise_fit
        progress_bar.progress(18)

        def extract_best_arima_order(stepwise_fit):
            # Search for the line starting with "Best model:"
            for line in stepwise_fit.split('\n'):
                if line.startswith("Best model:"):
                    # Extract numbers within parentheses
                    order = tuple(map(int, line.split('ARIMA')[1].split('(')[1].split(')')[0].split(',')))
                    return order
            return None
        arima_order = stepwise_fit.order
        arima_order
        mp, md, mq = arima_order
        progress_bar.progress(19)

        stepwise_fit = auto_arima(S,trace=True,suppress_warnings=True)
        stepwise_fit
        progress_bar.progress(20)

        def extract_best_arima_order(stepwise_fit):
            # Search for the line starting with "Best model:"
            for line in stepwise_fit.split('\n'):
                if line.startswith("Best model:"):
                    # Extract numbers within parentheses
                    order = tuple(map(int, line.split('ARIMA')[1].split('(')[1].split(')')[0].split(',')))
                    return order
            return None
        arima_order = stepwise_fit.order
        arima_order
        sp, sd, sq = arima_order
        progress_bar.progress(21)


        import statsmodels.api as sm

        arima_order = arima_order
        seasonal_order = (hp, hd, hq, SN)  
        progress_bar.progress(22)

        model = sm.tsa.statespace.SARIMAX(H, order=arima_order, seasonal_order=seasonal_order)
        model = model.fit()
        progress_bar.progress(23)

        start=len(H_train)
        end=len(H_train)+len(C_test)-1
        Hpred = model.predict(start=start,end=end)
        progress_bar.progress(24)

        Hpred_future = model.predict(start=end,end=end+DD)
        progress_bar.progress(25)


        import statsmodels.api as sm


        arima_order = arima_order
        seasonal_order = (cp, cd, cq, SN)  
        progress_bar.progress(26)

        model = sm.tsa.statespace.SARIMAX(C, order=arima_order, seasonal_order=seasonal_order)
        model = model.fit()
        progress_bar.progress(27)

        start=len(C_train)
        end=len(C_train)+len(C_test)-1
        Cpred = model.predict(start=start,end=end)
        progress_bar.progress(28)

        Cpred_future = model.predict(start=end,end=end+DD)
        progress_bar.progress(29)


        import statsmodels.api as sm


        arima_order = arima_order
        seasonal_order = (mp, md, mq, SN)  
        progress_bar.progress(30)

        model = sm.tsa.statespace.SARIMAX(M, order=arima_order, seasonal_order=seasonal_order)
        model = model.fit()
        progress_bar.progress(31)

        start=len(M_train)
        end=len(M_train)+len(M_test)-1
        Mpred = model.predict(start=start,end=end)
        progress_bar.progress(32)


        Mpred_future = model.predict(start=end,end=end+DD)
        progress_bar.progress(33)



        import statsmodels.api as sm

        arima_order = arima_order
        seasonal_order = (sp, sd, sq, SN)  
        progress_bar.progress(34)

        model = sm.tsa.statespace.SARIMAX(S, order=arima_order, seasonal_order=seasonal_order)
        model = model.fit()
        progress_bar.progress(35)

        start=len(S_train)
        end=len(S_train)+len(S_test)-1
        Spred = model.predict(start=start,end=end)
        progress_bar.progress(36)

        Spred_future = model.predict(start=end,end=end+DD)
        progress_bar.progress(37)



        # Assuming df.index is already set to datetime
        last_date = df.index[-2]  # Get the second to last date from the index
        start_date = last_date + pd.tseries.offsets.BDay(1)  # Calculate the start date as one business day after the last date
        progress_bar.progress(38)

        dates = [start_date + pd.Timedelta(days=idx) for idx in range(43)]  # Generate a list of dates starting from 'start_date'
        progress_bar.progress(39)


        # Filter out the weekend dates from the list
        market_dates = [date for date in dates if date.weekday() < 5]
        progress_bar.progress(40)

        Date = pd.Series(market_dates )
        Date
        progress_bar.progress(41)

        df3 = pd.DataFrame({'Date':Date,'Cpred_future': Cpred_future, 'Mpred_future': Mpred_future, 'Spred_future': Spred_future, 'Hpred_future': Hpred_future})
        df3
        progress_bar.progress(42)

        import matplotlib.pyplot as plt
        import pandas as pd
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        # Assuming df3 and df are already defined and Ticker is defined
        progress_bar.progress(45)

        # Convert 'Date' to datetime if it's not already
        df3['Date'] = pd.to_datetime(df3['Date'])
        progress_bar.progress(46)

        # Set the 'Date' column as the index of the DataFrame
        df3.set_index('Date', inplace=True)
        progress_bar.progress(47)

        # Create a figure and a set of subplots
        fig, axs = plt.subplots(2, 1, figsize=(20, 12))  # Adjusts the figure size for two subplots
        progress_bar.progress(48)

        # Plotting M and S predictions on the first subplot
        axs[0].plot(df3.index, df3['Mpred_future'], label='M predictions', marker='o', color='blue')
        axs[0].plot(df3.index, df3['Spred_future'], label='S predictions', marker='x', color='red')
        axs[0].set_title(f'Zoomed Forecast MACD of {Ticker}')
        axs[0].set_xlabel('Date')
        axs[0].set_ylabel('Values')
        axs[0].legend()
        axs[0].grid(True)
        axs[0].tick_params(axis='x', rotation=45)

        # Plotting Close Future predictions on the second subplot
        axs[1].plot(df3.index, df3['Cpred_future'], label='Close Future', marker='o', color='blue')
        axs[1].set_title(f'Zoomed Forecast Closing of {Ticker} Start Date {start_date1}')
        axs[1].set_xlabel('Date')
        axs[1].set_ylabel('Values')
        axs[1].legend()
        axs[1].grid(True)
        axs[1].tick_params(axis='x', rotation=45)


        plt.tight_layout()  # Adjusts the subplot params so that subplots are nicely fit in the figure
        st.pyplot(fig)  # Display the figure in Streamlit
        progress_bar.progress(49)

        # Construct the filename with today's date and ticker symbol
        filename = f"{today}_{Ticker}_Forecast.png"

        # Construct the path
        path = f"/Users/rajghotra/Library/CloudStorage/GoogleDrive-enterpriseghotra@gmail.com/My Drive/FileDrop/{Ticker}/{filename}"

        # Extract the directory path
        dir_path = os.path.dirname(path)

        # Check if the directory exists, if not create it
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Directory {dir_path} created.")
        else:
            print(f"Directory {dir_path} already exists.")

        plt.savefig(path)

        # Print the path for confirmation
        print(f"File saved as: {path}")
        plt.show()

        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import pandas as pd
        import numpy as np
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        progress_bar.progress(50)
        progress_bar.progress(54)
        progress_bar.progress(55)
        progress_bar.progress(56)
        progress_bar.progress(57)
        progress_bar.progress(58)
        progress_bar.progress(59)
        progress_bar.progress(60)
        progress_bar.progress(61)
        progress_bar.progress(62)
        progress_bar.progress(63)
        # Assuming 'df' and 'df3' are your DataFrames, and their indexes are of datetime type.
        # Also assuming 'df' already has 'MACD', 'Signal', 'Close' columns calculated.
        # 'df3' should contain your future predictions 'Mpred_future', 'Spred_future', 'Cpred_future', 'Hpred_future'.

        # Sorting the DataFrame by the index (date) to ensure the data is in chronological order
        df = df.sort_index()
        progress_bar.progress(51)

        # Calculate the Histogram if not already done
        df['Histogram'] = df['MACD'] - df['Signal']
        progress_bar.progress(52)

        # Creating a figure and a grid of subplots
        fig, axs = plt.subplots(5, 1, figsize=(14.875, 19.25), dpi=300)
        fig.suptitle(f"{Ticker}-Data Used for Forecasting {start_date1} to {today} for {DD} Days Forecast", fontsize=25, y=.99)
        # Plotting the Close price on axs[0]
        axs[4].plot(df.index, df['Close'], label='Close', color='Black')
        axs[4].set_title('Close Price')
        axs[4].legend(loc='upper left')
        axs[4].grid(True)

        # Formatting the date to ensure that the date does not overlap
        axs[4].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=45))
        axs[4].xaxis.set_major_formatter(mdates.ConciseDateFormatter(axs[0].xaxis.get_major_locator()))
        # Plotting MACD and Signal Line on axs[1]
        axs[1].plot(df.index, df['MACD'], label='MACD', color='blue', linewidth=1.5)
        axs[1].plot(df.index, df['Signal'], label='Signal Line', color='red', linewidth=1.5)
        # Plotting the Histogram as bar plot on axs[1]
        axs[1].bar(df.index, df['Histogram'], label='Histogram', color='grey', alpha=0.3)
        axs[1].set_title('MACD, Signal Line, and Histogram')
        axs[1].legend(loc='upper left')
        axs[1].grid(True)
        # Formatting the date for the second subplot
        axs[1].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=45))
        axs[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(axs[1].xaxis.get_major_locator()))
        # Forecast plots
        # MACD and Signal future predictions
        axs[2].plot(df.index, df['MACD'], label='MACD', color='blue')
        axs[2].plot(df.index, df['Signal'], label='Signal', color='red')
        axs[2].plot(df3.index[-1000:], df3['Mpred_future'][-1000:], label='MACD Future', linestyle='--', color='blue')
        axs[2].plot(df3.index[-1000:], df3['Spred_future'][-1000:], label='Signal Future', linestyle='--', color='red')
        axs[2].set_title('Forecast MACD and Signal Line')
        axs[2].legend()
        # Closing price and future prediction
        axs[3].plot(df.index, df['Close'], label='Closed', color='Black')
        axs[3].plot(df3.index[-1000:], df3['Cpred_future'][-1000:], label='Closing Future', linestyle='--', color='Blue')
        axs[3].set_title('Forecast Closing Price')
        axs[3].legend()
        # Histogram and future prediction
        width = 0.22
        axs[0].bar(df.index, df['Histogram'], width, label='Histogram', color='blue')
        axs[0].bar(df3.index[-1000:], df3['Hpred_future'][-1000:], width, label='Histogram Future', color='green')
        axs[0].set_title('Forecast Histogram')
        axs[0].legend()
        # General settings for all subplots
        for ax in axs:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            ax.grid(True)
            ax.set_xlabel('Date')
            ax.set_ylabel('Value')
        plt.tight_layout(pad=1)
        st.pyplot(fig)  # Display the figure in Streamlit
        progress_bar.progress(100)
        st.success("Model run successfully!")
