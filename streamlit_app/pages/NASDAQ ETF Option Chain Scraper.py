import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.title("NASDAQ ETF Option Chain Scraper")

URL = "https://www.nasdaq.com/market-activity/etf/puls/option-chain"

# Function to scrape data
def scrape_data():
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find(class_="jupiter22-options-chain__container show-table")

    headers = []
    for th in table.find_all('th'):
        headers.append(th.text.strip())

    rows = []
    for tr in table.find_all('tr')[1:]:  # Skip the header row
        cells = tr.find_all('td')
        row = [cell.text.strip() for cell in cells]
        if row:  # Only add rows that are not empty
            rows.append(row)

    return headers, rows

# Display data in Streamlit
headers, rows = scrape_data()

if headers and rows:
    df = pd.DataFrame(rows, columns=headers)
    st.dataframe(df)
else:
    st.write("No data found or unable to scrape the data.")

if st.button('Refresh Data'):
    headers, rows = scrape_data()
    if headers and rows:
        df = pd.DataFrame(rows, columns=headers)
        st.dataframe(df)
    else:
        st.write("No data found or unable to scrape the data.")
