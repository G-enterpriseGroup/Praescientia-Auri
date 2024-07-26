import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Setup the Selenium driver
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Fetch the webpage
url = "https://www.tradingview.com/watchlists/139248623/"
driver.get(url)

# Extract content using XPath
xpath = "/html/body/div[4]/div[4]/div/div/div[2]/div"
content = driver.find_element(By.XPATH, xpath).text

# Close the driver
driver.quit()

# Display content in Streamlit
st.title("TradingView Watchlist Content")
st.write(content)
