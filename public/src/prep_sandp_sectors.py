# *** Run this script after prep_sandp.py ***
import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


# Communication Services Select Sector (XLC)   
# Consumer Discretionary Select Sector (XLY)   
# Consumer Staples Select Sector (XLP)   
# Energy Select Sector (XLE)   
# Financial Select Sector (XLF)   
# Health Care Select Sector (XLV)   
# Industrial Select Sector (XLI)   
# Materials Select Sector (XLB)   
# Real Estate Select Sector (XLRE)   
# Technology Select Sector (XLK)   
# Utilities Select Sector (XLU)

sector_map = {
    'Industrials': 'XLI',
    'Health Care': 'XLV',
    'Information Technology': 'XLK',
    'Communication Services': 'XLC',
    'Consumer Discretionary': 'XLY',
    'Utilities': 'XLU',
    'Financials': 'XLF',
    'Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Consumer Staples': 'XLP',
    'Energy': 'XLE'
}

def prep_spy_sectors():
    
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    file_name = 'spysectors'
    file_path = '../data/' + file_name + '.json'
    # comps_df = pd.read_html(url)[0]
    # comps_grp = comps_df.groupby('GICS Sector')
    
    comps_df  = pd.read_json('../data/s&p500.json', orient='records')
    comps_df['SectorKey'] = comps_df['Sector'].map(sector_map)
    # print(comps_df.head())

    res_list = []
    if comps_df.empty:
        raise ValueError("No data found in the S&P 500 components DataFrame.")
    
    for k,v in sector_map.items():
        comps_list = comps_df[comps_df['SectorKey'] == v][['Name', 'Ticker']].values.tolist()
        # print(comps_list)

        sec_items = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Exchange': ''
            }
            sec_items.append(d)

        sec_dict = {
            'Name': k,
            'Ticker': v,
            'Comps': sec_items
        }
        res_list.append(sec_dict)

        
    if res_list:
        with open(file_path, 'w') as fp:
            json.dump(res_list, fp)

        print('S&P 500 sectors data read and json write was successfull.')

        try:
            comps_df.to_csv('../data/spysectors.csv', index=False, encoding='utf-8-sig')
            print('S&P 500 sectors data saved to CSV successfully.')
        except Exception as e:
            logging.error(str(e))
            print(f'Failed to save S&P 500 sectors data to CSV. {e}')

    else:
        raise ValueError("Failed to collect SPY sectors.")
            


if __name__ == '__main__':

    prep_spy_sectors()
