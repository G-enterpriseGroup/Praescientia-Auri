import streamlit as st
import pandas as pd
import requests

# URL of the text file
url = "https://www.tradingview.com/978c08d6-1b5b-4b3f-8b77-2c67ce670c8e"

# Fetch the content from the URL
response = requests.get(url)

# Ensure the request was successful
if response.status_code == 200:
    # Process the content as needed
    content = response.text

    # Convert the content to a DataFrame (assuming it's CSV formatted text)
    from io import StringIO
    df = pd.read_csv(StringIO(content))

    # Display the DataFrame
    st.dataframe(df)
else:
    st.error("Failed to fetch the data. Please check the URL.")

# Run the Streamlit app with: streamlit run your_script_name.py
