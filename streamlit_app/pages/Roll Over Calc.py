import streamlit as st
import yfinance as yf
import pandas as pd
st.set_page_config(layout="wide")
def display_put_options_all_dates(ticker_symbol, cost, old_premium, old_strike):
    try:
        ticker = yf.Ticker(ticker_symbol)
        expiration_dates = ticker.options
        if not expiration_dates:
            st.warning(f"No options data available for ticker {ticker_symbol}.")
            return
        
        # Constant Old Max Loss calculation
        old_max_loss = (old_strike * 100) - ((cost * 100) + (old_premium * 100))
        
        for chosen_date in expiration_dates:
            st.markdown(f"### Processing expiration date: {chosen_date}")
            options_chain = ticker.option_chain(chosen_date)
            puts = options_chain.puts

            if puts.empty:
                st.warning(f"No puts available for expiration date {chosen_date}.")
                continue

            table_data = []
            for _, row in puts.iterrows():
                # Roll Result: Prior Premium + Last Price
                roll_result = old_premium + row["lastPrice"]
                # New Max Loss uses roll_result instead of lastPrice
                new_max_loss = (old_strike * 100) - ((cost * 100) + (roll_result * 100))
                # New Max Loss with New Strike uses the current option's strike
                new_max_loss_with_new_strike = (row["strike"] * 100) - ((cost * 100) + (roll_result * 100))
                # Difference between Old Max Loss and New Max Loss
                loss_diff = old_max_loss - new_max_loss

                table_data.append({
                    "Contract": row["contractSymbol"],
                    "Strike": f"{row['strike']:.2f}",
                    "Bid Price": f"{row['bid']:.2f}",
                    "Ask Price": f"{row['ask']:.2f}",
                    "Last Price": f"{row['lastPrice']:.2f}",
                    "Roll Result": f"{roll_result:.2f}",
                    "Old Max Loss": f"{old_max_loss:.2f}",
                    "New Max Loss": f"{new_max_loss:.2f}",
                    "Old Max Loss - New Max Loss": f"{loss_diff:.2f}",
                    "New Max Loss with New Strike": f"{new_max_loss_with_new_strike:.2f}"
                })

            df = pd.DataFrame(table_data)

            # Apply conditional formatting to highlight rows where Strike equals old_strike.
            def highlight_row(row):
                if float(row["Strike"]) == old_strike:
                    return ['background-color: yellow'] * len(row)
                else:
                    return [''] * len(row)

            styled_df = df.style.apply(highlight_row, axis=1)
            st.write(styled_df)
        
        st.success("All expiration dates processed successfully.")
    except Exception as e:
        st.error(f"An error occurred: {e}")

st.title("Put Options Analysis")

with st.form("options_form"):
    ticker_symbol = st.text_input("Enter the ticker symbol:", value="AAPL").strip().upper()
    cost = st.number_input("Enter the cost of the shares acquired:", value=0.0, format="%.2f")
    old_premium = st.number_input("Enter the old premium paid for the protective put:", value=0.0, format="%.2f")
    old_strike = st.number_input("Enter the strike price of the protective put:", value=0.0, format="%.2f")
    submitted = st.form_submit_button("Submit")

if submitted:
    with st.spinner("Fetching and processing data..."):
        display_put_options_all_dates(ticker_symbol, cost, old_premium, old_strike)
