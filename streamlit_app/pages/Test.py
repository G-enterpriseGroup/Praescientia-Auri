import yfinance as yf
import pandas as pd

# Define the ticker and the ex-dividend dates of interest
ticker = "PULS"
dates = ["2023-04-03", "2023-05-01", "2023-06-01", "2023-07-03", 
         "2023-08-01", "2023-09-01", "2023-10-02", "2023-11-01", "2023-12-01"]

# Download historical data for the ticker
data = yf.download(ticker, start="2023-04-01", end="2023-12-31")

# Ensure columns for calculations are in place
data['Open'] = data['Open'].fillna(method='ffill')
data['Close'] = data['Close'].fillna(method='ffill')

# Calculate Heikin Ashi bars
heikin_ashi = pd.DataFrame(index=data.index)
heikin_ashi['open'] = (data['Open'].shift(1) + data['Close'].shift(1)) / 2
heikin_ashi['close'] = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4
heikin_ashi['high'] = data[['High', 'Open', 'Close']].max(axis=1)
heikin_ashi['low'] = data[['Low', 'Open', 'Close']].min(axis=1)

# Replace NaN values in 'open' column for first row if necessary
heikin_ashi['open'].fillna(data['Open'], inplace=True)

# Filter the data for the specific ex-dividend dates and print high and low
print("High and Low prices on ex-dividend dates using Heikin Ashi:")
for date in dates:
    if date in heikin_ashi.index:
        high = heikin_ashi.loc[date, 'high']
        low = heikin_ashi.loc[date, 'low']
        print(f"Date: {date}, High: {high}, Low: {low}")
