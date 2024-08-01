=from bs4 import BeautifulSoup
import streamlit as st

# HTML content provided
html_content = '''
<button class="rangeButtonRed-tEo1hPMj rangeButton-tEo1hPMj selected-tEo1hPMj"><span class="content-tEo1hPMj"><span>1 day</span><span class="change-tEo1hPMj">−1.68%</span></span></button>
<button class="rangeButtonRed-tEo1hPMj rangeButton-tEo1hPMj"><span class="content-tEo1hPMj"><span>5 days</span><span class="change-tEo1hPMj">−0.16%</span></span></button>
<button class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"><span class="content-tEo1hPMj"><span>1 month</span><span class="change-tEo1hPMj">1.02%</span></span></button>
<button class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"><span class="content-tEo1hPMj"><span>6 months</span><span class="change-tEo1hPMj">21.41%</span></span></button>
<button class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"><span class="content-tEo1hPMj"><span>Year to date</span><span class="change-tEo1hPMj">16.68%</span></span></button>
<button class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"><span class="content-tEo1hPMj"><span>1 year</span><span class="change-tEo1hPMj">11.96%</span></span></button>
<button class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"><span class="content-tEo1hPMj"><span>5 years</span><span class="change-tEo1hPMj">308.34%</span></span></button>
<button class="rangeButtonGreen-tEo1hPMj rangeButton-tEo1hPMj"><span class="content-tEo1hPMj"><span>All time</span><span class="change-tEo1hPMj">‪170.03 K‬%</span></span></button>
'''

# Parse the HTML content
soup = BeautifulSoup(html_content, 'html.parser')

# Extract performance data
performance_data = []
buttons = soup.find_all('button', class_='rangeButton-tEo1hPMj')
for button in buttons:
    time_period = button.find('span', class_='content-tEo1hPMj').find('span').text
    change = button.find('span', class_='change-tEo1hPMj').text
    performance_data.append((time_period, change))

# Create a Streamlit app to display the data
st.title('AAPL Performance Data')

for time_period, change in performance_data:
    st.write(f"{time_period}: {change}")
