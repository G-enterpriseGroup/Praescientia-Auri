import yfinance as yf
import pandas as pd
import streamlit as st
import warnings
from requests.exceptions import HTTPError
import requests
from lxml import html

st.set_page_config(page_title="DIV MATRIX", layout="wide")

# Suppress warnings
warnings.filterwarnings("ignore")

def fetch_ttm_dividend_yield(tickers):
    data = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            long_name = info.get("longName", "N/A")

            # Determine if it's a stock or ETF
            quote_type = info.get("quoteType", "N/A").lower()
            if "etf" in quote_type:
                link = f"https://stockanalysis.com/etf/{ticker}/"
            else:
                link = f"https://stockanalysis.com/stocks/{ticker}/"

            additional_data = get_additional_stock_data(ticker)

            data.append([ticker, long_name, link] + additional_data)
        except HTTPError:
            # Handle HTTP errors silently
            data.append([ticker, "Error fetching data", "N/A", "N/A"])
        except Exception:
            # Handle all other errors silently
            data.append([ticker, "Error fetching data", "N/A", "N/A"])

    columns = ["Ticker", "Long Name", "StockAnalysis Link", 
               "DIVID", "1 Day", "5 Days", "1 Month", "6 Months", "YTD", "1 Year", "5 Years", "All Time"]
    df = pd.DataFrame(data, columns=columns)
    return df

# Function to get additional stock or ETF data
def get_additional_stock_data(ticker):
    base_url = f"https://www.tradingview.com/symbols/{ticker}/"
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            tree = html.fromstring(response.content)

            # Attempt both stock and ETF XPaths
            try:
                # First try stock XPath
                divid = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[3]/div[2]/div/div[2]/div[2]/div[1]/div/text()')[0].strip()
                day_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[1]/span/span[2]/text()')[0].strip()
                day_5 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[2]/span/span[2]/text()')[0].strip()
                month_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[3]/span/span[2]/text()')[0].strip()
                month_6 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[4]/span/span[2]/text()')[0].strip()
                ytd = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[5]/span/span[2]/text()')[0].strip()
                year_1 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[6]/span/span[2]/text()')[0].strip()
                year_5 = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[7]/span/span[2]/text()')[0].strip()
                all_time = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[1]/div[2]/div/div[2]/div/div[2]/button[8]/span/span[2]/text()')[0].strip()
            except IndexError:
                divid = tree.xpath('//*[@id="js-category-content"]/div[2]/div/section/div[2]/div[2]/div/div[3]/div[2]/div[1]/div/text()')[0].strip()
                day_1 = tree.xpath('//button[span/span[text()="1 day"]]/span/span[@class="change-tEo1hPMj"]/text()')[0].strip()
                day_5 = tree.xpath('//button[span/span[text()="5 days"]]/span/span[@class="change-tEo1hPMj"]/text()')[0].strip()
                month_1 = tree.xpath('//button[span/span[text()="1 month"]]/span/span[@class="change-tEo1hPMj"]/text()')[0].strip()
                month_6 = tree.xpath('//button[span/span[text()="6 months"]]/span/span[@class="change-tEo1hPMj"]/text()')[0].strip()
                ytd = tree.xpath('//button[span/span[text()="Year to date"]]/span/span[@class="change-tEo1hPMj"]/text()')[0].strip()
                year_1 = tree.xpath('//button[span/span[text()="1 year"]]/span/span[@class="change-tEo1hPMj"]/text()')[0].strip()
                year_5 = tree.xpath('//button[span/span[text()="5 years"]]/span/span[@class="change-tEo1hPMj"]/text()')[0].strip()
                all_time = tree.xpath('//button[span/span[text()="All time"]]/span/span[@class="change-tEo1hPMj"]/text()')[0].strip()

            return [divid, day_1, day_5, month_1, month_6, ytd, year_1, year_5, all_time]
        else:
            return ["N/A"] * 9
    except Exception as e:
        return ["N/A"] * 9

def main():
    st.title("TTM Dividend Yield and Stock Data Fetcher")

    st.markdown("""
    Enter stock or ETF tickers below (separated by commas) to fetch the TTM dividend yield.
    The results will also include additional stock data and a link to StockAnalysis for more information.
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
