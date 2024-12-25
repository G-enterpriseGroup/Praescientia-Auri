import yfinance as yf
import pandas as pd
import streamlit as st
import warnings
from requests.exceptions import HTTPError

# Suppress warnings
warnings.filterwarnings("ignore")

def fetch_ttm_dividend_yield(tickers):
    data = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            long_name = info.get("longName", "N/A")
            dividend_yield = info.get("trailingAnnualDividendYield", None)

            if dividend_yield is not None:
                dividend_yield_percentage = dividend_yield * 100
            else:
                dividend_yield_percentage = "N/A"

            # Determine if it's a stock or ETF
            quote_type = info.get("quoteType", "N/A").lower()
            if "etf" in quote_type:
                link = f"https://stockanalysis.com/etf/{ticker}/"
            else:
                link = f"https://stockanalysis.com/stocks/{ticker}/"

            data.append([ticker, long_name, dividend_yield_percentage, link])
        except HTTPError:
            # Handle HTTP errors silently
            data.append([ticker, "Error fetching data", "N/A", "N/A"])
        except Exception:
            # Handle all other errors silently
            data.append([ticker, "Error fetching data", "N/A", "N/A"])

    df = pd.DataFrame(data, columns=["Ticker", "Long Name", "TTM Dividend Yield (%)", "StockAnalysis Link"])
    return df

def main():
    st.title("TTM Dividend Yield Fetcher")

    st.markdown("""
    Enter stock or ETF tickers below (separated by commas) to fetch the TTM dividend yield.
    The results will also include a link to StockAnalysis for more information.
    """)

    tickers_input = st.text_input("Enter Tickers (comma-separated):")

    if st.button("Fetch Data"):
        if tickers_input:
            tickers = [ticker.strip() for ticker in tickers_input.split(",")]

            with st.spinner("Fetching data..."):
                result_df = fetch_ttm_dividend_yield(tickers)

            st.success("Data fetched successfully!")
            st.write(result_df)

            # Provide download option
            csv = result_df.to_csv(index=False)
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name="ttm_dividend_yield.csv",
                mime="text/csv",
            )
        else:
            st.error("Please enter at least one ticker.")

if __name__ == "__main__":
    main()
