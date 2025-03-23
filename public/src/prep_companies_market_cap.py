# new source
# Manually download, rename, and move "CompaniesMarketCap.csv" from https://companiesmarketcap.com/ to current directory.
# Note: pandas read_csv replaces ("Nano Labs","NA") to ("Nano Labs", NaN) make sure to fix this.

# old source
# Manually download, rename, and move "nasdaq_screener.csv" file from [https://www.nasdaq.com/market-activity/stocks/screener] to current directory
# fix issues 


import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def read_prep_companies_market_cap():
    
    file_name = 'stocks'
    file_path = '../data/' + file_name + '.json'

    try:
        df_raw = pd.read_csv('../data/CompaniesMarketCap.csv')

        df_raw = df_raw[~df_raw['Symbol'].isnull()]
        df_raw['Symbol'] = df_raw.apply(lambda x: x['Symbol'].strip(), axis=1)
        df_new = df_raw[df_raw['marketcap'] > 0].reset_index(drop=True)

        res_list = []
        for i in df_new.index:
            r = df_new.loc[i]
            d = {
                'Rank': int(r['Rank']),
                'Name': r['Name'],
                'Ticker': r['Symbol'],
                'MarketCap': int(r['marketcap']),
                'Country': r['country']
            }
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('Companies market cap data read was successfull.')

    except Exception as e:
        logging.error(str(e))
        print(f'Companies market cap data read failed. {e}')



if __name__ == '__main__':

    read_prep_companies_market_cap()