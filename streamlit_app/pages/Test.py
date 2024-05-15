import yfinance as yf
import pandas as pd

# Define the ticker and the ex-dividend dates of interest
ticker = "PULS"
dates = ["2023-04-03", "2023-05-01", "2023-06-01", "2023-07-03", 
         "2023-08-01", "2023-09-01", "2023-10-02", "2023-11-01", "2023-12-01"]

# Download historical data for the ticker
data = yf.download(ticker, start="2023-04-01", end="2023-12-31")

# Calculate Heikin Ashi bars
heikin_ashi = pd.DataFrame(index=data.index)
heikin_ashi['close'] = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4
heikin_ashi['open'] = (data['Open'].shift() + data['Close'].shift()) / 2
heikin_ashi['high'] = data[['High', 'open', 'close']].max(axis=1)
heikin_ashi['low'] = data[['Low', 'open', 'close']].min(axis=1)
heikin_ashi.fillna(method='bfill', inplace=True)

# Filter the data for the specific ex-dividend dates and print high and low
print("High and Low prices on ex-dividend dates using Heikin Ashi:")
for date in dates:
    if date in heikin_ashi.index:
        high = heikin_ashi.loc[date, 'high']
        low = heikin_ashi.loc[date, 'low']
        print(f"Date: {date}, High: {high}, Low: {low}")
