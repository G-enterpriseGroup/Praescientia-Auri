import yfinance as yf
from datetime import datetime, timedelta

# User inputs
ticker = 'AAPL'  # Example, replace with user input
interval = '1d'  # Example, replace with user input

# Adjust date range to ensure the end date is not today's date
end_date = datetime.now() - timedelta(days=1)
start_date = end_date - timedelta(days=30)  # Adjust based on the desired interval

try:
    # Fetch data with adjusted date range
    data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval=interval)
    if data.empty:
        raise ValueError(f"No data found for {ticker} within the specified date range.")
    # Proceed with data processing and visualization
except Exception as e:
    # Handle exceptions, including no data found, delisted symbols, etc.
    print(f"An error occurred: {e}")
