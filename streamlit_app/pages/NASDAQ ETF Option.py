import requests
import json
import streamlit as st

def get_options_chain(symbol):
    api_key = "QEfbgq5dDyXiF9uqrJh3"
    url = f"https://data.nasdaq.com/api/v3/datasets/OPTIONCHAIN/{symbol}.json?api_key={api_key}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None

def main():
    st.title("Options Chain Data")
    
    symbol = st.text_input("Enter the stock or ETF symbol:")
    
    if st.button("Get Options Chain"):
        options_chain = get_options_chain(symbol)
        
        if options_chain:
            st.json(options_chain)
        else:
            st.error(f"Failed to retrieve data for {symbol}")

if __name__ == "__main__":
    main()
