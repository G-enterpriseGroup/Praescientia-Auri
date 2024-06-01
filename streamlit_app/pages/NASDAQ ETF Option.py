import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Function to scrape the data
def scrape_options(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    tables = soup.find_all('table')
    calls_table = tables[0]
    puts_table = tables[1]
    
    def parse_table(table):
        headers = [header.text.strip() for header in table.find_all('th')]
        rows = []
        for row in table.find_all('tr')[1:]:
            data = [cell.text.strip() for cell in row.find_all('td')]
            rows.append(data)
        return pd.DataFrame(rows, columns=headers)
    
    calls_df = parse_table(calls_table)
    puts_df = parse_table(puts_table)
    
    return calls_df, puts_df

# Streamlit app
st.title("Option Chain Scraper")
st.write("Scrapes the calls and puts for the given ETF.")

url = "https://www.nasdaq.com/market-activity/etf/puls/option-chain"
calls_df, puts_df = scrape_options(url)

st.subheader("Calls")
st.dataframe(calls_df)

st.subheader("Puts")
st.dataframe(puts_df)
