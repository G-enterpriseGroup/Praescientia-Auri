import streamlit as st
import pandas as pd
from urllib.request import urlopen as uReq
from bs4 import BeautifulSoup as soup
import itertools
import datetime

def replace_blank(x):
    return 0 if x == '' else x

def fetch_option_chain(ticker, date_index):
    url = f'https://www.nasdaq.com/symbol/{ticker}/option-chain?dateindex={date_index}'
    uClient = uReq(url)
    page_html = uClient.read()
    uClient.close()
    page_soup = soup(page_html, 'html.parser')
    attributes = page_soup.findAll('div', {'class': 'OptionsChain-chart'})
    attribute = attributes[0]
    tables = attribute.find_all('table')
    table = tables[0]
    rows = table.find_all('tr')
    iterrows = iter(rows)
    next(iterrows)
    data = {
        'CallsKey': [], 'LastCallKey': [], 'ChgCallKey': [], 'BidCallKey': [], 'AskCallKey': [], 
        'VolCalls': [], 'OpenIntCalls': [], 'Root': [], 'Strike': [], 
        'PutsKey': [], 'LastPutKey': [], 'ChgPutKey': [], 'BidPutKey': [], 'AskPutKey': [], 
        'VolPuts': [], 'OpenIntPuts': []
    }
    for row in iterrows:
        columns = row.find_all('td')
        data['CallsKey'].append(replace_blank(columns[0].text))
        data['LastCallKey'].append(replace_blank(columns[1].text))
        data['ChgCallKey'].append(replace_blank(columns[2].text))
        data['BidCallKey'].append(replace_blank(columns[3].text))
        data['AskCallKey'].append(replace_blank(columns[4].text))
        data['VolCalls'].append(replace_blank(columns[5].text))
        data['OpenIntCalls'].append(replace_blank(columns[6].text))
        data['Root'].append(replace_blank(columns[7].text))
        data['Strike'].append(replace_blank(columns[8].text))
        data['PutsKey'].append(replace_blank(columns[9].text))
        data['LastPutKey'].append(replace_blank(columns[10].text))
        data['ChgPutKey'].append(replace_blank(columns[11].text))
        data['BidPutKey'].append(replace_blank(columns[12].text))
        data['AskPutKey'].append(replace_blank(columns[13].text))
        data['VolPuts'].append(replace_blank(columns[14].text))
        data['OpenIntPuts'].append(replace_blank(columns[15].text))
    return data

def main():
    st.title('NASDAQ Option Chain Scraper')
    ticker = st.text_input('Enter Ticker Symbol:')
    if st.button('Fetch Data'):
        all_data = {key: [] for key in ['CallsKey', 'LastCallKey', 'ChgCallKey', 'BidCallKey', 'AskCallKey', 
                                        'VolCalls', 'OpenIntCalls', 'Root', 'Strike', 'PutsKey', 
                                        'LastPutKey', 'ChgPutKey', 'BidPutKey', 'AskPutKey', 
                                        'VolPuts', 'OpenIntPuts']}
        for i in range(1, 14):
            data = fetch_option_chain(ticker, i)
            for key in all_data.keys():
                all_data[key].extend(data[key])
        
        df = pd.DataFrame(all_data)
        st.write(df)
        
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{ticker}_{now}.csv"
        df.to_csv(file_name, index=False)
        
        st.success(f"Data saved to {file_name}")

if __name__ == "__main__":
    main()
