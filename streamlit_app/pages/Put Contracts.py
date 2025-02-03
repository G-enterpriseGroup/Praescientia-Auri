import streamlit as st
import yfinance as yf
import pandas as pd

def get_put_options_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    expiration_dates = ticker.options
    if not expiration_dates:
        st.error(f"No options data available for ticker {ticker_symbol}.")
        return pd.DataFrame()
    
    all_options = pd.DataFrame()
    
    for exp_date in expiration_dates:
        st.subheader(f"Expiration Date: {exp_date}")
        try:
            options_chain = ticker.option_chain(exp_date)
            puts = options_chain.puts
            if puts.empty:
                st.info(f"No put options available for expiration date {exp_date}.")
                continue
            
            # Keep only the desired columns and rename them
            puts = puts[["contractSymbol", "strike", "bid", "ask", "lastPrice"]].copy()
            puts.columns = ["Contract", "Strike", "Bid Price", "Ask Price", "Last Price"]
            puts["Expiration"] = exp_date  # add expiration date column for reference
            
            # Display the table in Streamlit
            st.dataframe(puts)
            
            all_options = pd.concat([all_options, puts], ignore_index=True)
        except Exception as e:
            st.error(f"Error processing expiration date {exp_date}: {e}")
    
    return all_options

def main():
    st.title("Options Put Data Viewer")
    ticker_symbol = st.text_input("Enter ticker symbol:", "AAPL").upper().strip()
    
    if ticker_symbol:
        if st.button("Fetch Options Data"):
            with st.spinner("Fetching options data..."):
                data = get_put_options_data(ticker_symbol)
            
            if not data.empty:
                csv_data = data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"{ticker_symbol}_put_options.csv",
                    mime="text/csv"
                )
            else:
                st.error("No put options data found.")

if __name__ == "__main__":
    main()
