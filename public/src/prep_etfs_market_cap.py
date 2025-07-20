# *** ETF RANKING AND MARKET CAP NO LONGER AVAILABLE WITH FINANCEDATABASE PACKAGE. ***
# *** KEEPING THE OLD FILE UNTIL NEW SOURCE FOR ETF RANKING AND MARKET CAP IS AVAILABLE. ***


import json
import pandas as pd
import requests
import financedatabase as fd
import re
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

def parse_marketcap(val):
    if isinstance(val, str):
        val = val.replace('$', '').replace(',', '').strip()
        if val.endswith('T'):
            return float(val[:-1]) * 1e12
        elif val.endswith('B'):
            return float(val[:-1]) * 1e9
        elif val.endswith('M'):
            return float(val[:-1]) * 1e6
        elif val == '0':
            return 0.0
    return None

def read_etfs():

    # Base URL for ETF listings
    base_url = 'https://8marketcap.com/etfs/'

    # Container for per-page DataFrames
    etf_dfs = []

    # Iterate through all 23 pages
    for page in range(1, 24):
        url = f"{base_url}?page={page}"
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the first table on the page
        tables = pd.read_html(response.text)
        etf_table = tables[0]
        etf_dfs.append(etf_table)

    # Concatenate all pages into one DataFrame
    all_etfs = pd.concat(etf_dfs, ignore_index=True)

    drop_index = all_etfs[(all_etfs['Name'].isna()) | (all_etfs['Name'].str.contains('Close Ad X'))].index
    # drop_index

    all_etfs = all_etfs.drop(index=drop_index).reset_index(drop=True)[['#', 'Name', 'Symbol', 'Market Cap']]
    all_etfs.columns = ['Rank', 'Name', 'Symbol', 'MarketCapTxt']
    all_etfs['Rank'] = all_etfs['Rank'].astype(int)
    all_etfs['MarketCap'] = all_etfs['MarketCapTxt'].apply(parse_marketcap)

    return all_etfs


def read_prep_etfs(use_csv=False):

    file_name = 'etfs_market_cap'
    file_path = '../data/' + file_name + '.json'

    res_list = []
    if use_csv:

        try:
            # df = pd.read_csv('etf_list.csv', index_col=False)
            # df['market_cap'] = df['market_cap'].replace({'\\$': '', ',': ''}, regex=True).astype('int')
            # df = df[df['market_cap'] > 0]
            # df.sort_values(['market_cap'], inplace=True, ascending=False)
            # df.reset_index(drop=True, inplace=True)
            df = read_etfs()
            for idx, row in df.iterrows():
                d = {
                    'Rank': row['Rank'],
                    'Name': row['Name'],
                    'Ticker': row['Symbol'],
                    'MarketCap': row['MarketCap'],
                    'Exchange': ""
                }
                res_list.append(d)

            with open(file_path, "w") as write_file:
                json.dump(res_list, write_file)

            print('ETFs data read was successfull.')

        except Exception as e:
            raise ValueError(f"Failed to prep ETF list. {e}")
    
    else:
        try:
            etf_df = fd.ETFs().select()
            etf_list = etf_df.index.tolist()
            print(len(etf_list))

            # Define a regex pattern that matches any character that is not alpahbetic.
            pattern = r"[^a-zA-Z]"

            drop_list = [s for s in etf_list if re.search(pattern, s)]
            print(len(drop_list))

            etf_list = list(set(etf_list).difference(drop_list))

            print(len(etf_list))

            final_etf_df = etf_df.loc[etf_list][['name']].reset_index(drop=False)
            for idx, row in final_etf_df.iterrows():
                d = {
                    'Rank': idx+1,
                    'Name': row['name'],
                    'Ticker': row['symbol'],
                    'MarketCap': "",
                    'Exchange': ""
                }
                res_list.append(d)

            return res_list
        
        except Exception as e:
            raise ValueError(f"Failed to prep ETF list. {e}")
        
    # TODO: ADD WRITE TO JSON FILE WHEN RANK AND MARKET CAP SOURCE BECOMES AVAILABLE


if __name__ == '__main__':
    read_prep_etfs(use_csv=True)