import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import io

def get_csv_content(url, xpath):
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode for Streamlit
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)
    
    # Simulate clicking the download button
    download_button = driver.find_element(By.XPATH, xpath)
    download_button.click()
    
    time.sleep(5)  # Wait for the download to complete and pop-up

    # Find the iframe or modal where the CSV data is presented (if applicable)
    csv_text = None
    try:
        csv_text = driver.find_element(By.TAG_NAME, 'pre').text
    except Exception as e:
        print(f"Error finding CSV data: {e}")

    driver.quit()
    return csv_text

# Streamlit app
st.title('TradingView Watchlist')

# Define the URL and XPath
watchlist_url = 'https://www.tradingview.com/watchlists/139248623/'
download_xpath = '/html/body/div[4]/div[4]/div/div/div[2]/div/div/section[1]/div/div/div[1]/div[2]/div[2]/span/svg'

# Get CSV content
csv_content = get_csv_content(watchlist_url, download_xpath)

# Display CSV content
if csv_content:
    csv_file = io.StringIO(csv_content)
    tickers_df = pd.read_csv(csv_file)
    st.write(tickers_df)
else:
    st.write("No CSV content found. Please ensure the watchlist is accessible and the XPath is correct.")
