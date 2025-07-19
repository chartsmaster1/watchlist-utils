
import json
import pandas as pd
import numpy as np
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

def sort_by_market_cap(df):
    """
    Sorts the DataFrame by MarketCap in descending order.
    """
    mc_df = pd.read_json('../data/stocks.json')
    mc_df['Ticker'] = np.where(mc_df['Ticker'] == 'BRK-B', 'BRK.B', mc_df['Ticker'])
    mc_df['Ticker'] = np.where(mc_df['Ticker'] == 'BF-A', 'BF.B', mc_df['Ticker'])

    sp_df = df.copy()
    sp_df.columns = ['Name', 'Ticker', 'Sector']
    sp_df = sp_df[~sp_df['Ticker'].isin(['GOOGL', 'FOXA', 'NWSA'])]

    sp_mc_df = (
        sp_df.merge(
            mc_df[['Ticker', 'MarketCap']],
            on='Ticker',
            how='left'
        )
        .sort_values(by='MarketCap', ascending=False)
    )

    return sp_mc_df


def read_prep_sandp():
    
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    file_name = 'spy'
    file_path = '../data/' + file_name + '.json'
    
    try:
        comps = pd.read_html(url)[0]
        comps_sorted = sort_by_market_cap(comps[['Security', 'Symbol', 'GICS Sector']])

        assert comps_sorted[comps_sorted['MarketCap'].isnull()].shape[0] == 0, "Fix the ticker issue before joining the two dataframes."

        comps_list = comps_sorted[['Name', 'Ticker', 'Sector', 'MarketCap']].values.tolist()
        
        res_list = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Exchange': '',
                'Sector': item[2],
                'MarketCap': item[3]
            }
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('S&P500 data read was successfull.')

    except Exception as e:
        logging.error(str(e))
        print(f'S&P500 data read failed. {e}')



if __name__ == '__main__':

    read_prep_sandp()