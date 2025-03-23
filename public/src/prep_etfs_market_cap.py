# *** ETF RANKING AND MARKET CAP NO LONGER AVAILABLE WITH FINANCEDATABASE PACKAGE. ***
# *** KEEPING THE OLD FILE UNTIL NEW SOURCE FOR ETF RANKING AND MARKET CAP IS AVAILABLE. ***


import json
import pandas as pd
import financedatabase as fd
import re
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def read_prep_etfs(use_csv=False):

    res_list = []
    if use_csv:

        try:
            df = pd.read_csv('etf_list.csv', index_col=False)
            df['market_cap'] = df['market_cap'].replace({'\\$': '', ',': ''}, regex=True).astype('int')
            df = df[df['market_cap'] > 0]
            df.sort_values(['market_cap'], inplace=True, ascending=False)
            df.reset_index(drop=True, inplace=True)
            for idx, row in df.iterrows():
                d = {
                    'Rank': idx+1,
                    'Name': row['name'],
                    'Ticker': row['symbol'],
                    'MarketCap': row['market_cap'],
                    'Exchange': ""
                }
                res_list.append(d)

            return res_list
        
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
    read_prep_etfs()