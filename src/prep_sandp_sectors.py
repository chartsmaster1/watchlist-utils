
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

def _set_sector(s):
    
    if s == 'Industrials':
        return 'XLI'
    elif s == 'Health Care':
        return 'XLV'
    elif s == 'Information Technology':
        return 'XLK'
    elif s == 'Communication Services':
        return 'XLC'
    elif s == 'Consumer Discretionary':
        return 'XLY'
    elif s == 'Utilities':
        return 'XLU'
    elif s == 'Financials':
        return 'XLF'
    elif s == 'Materials':
        return 'XLB'
    elif s == 'Real Estate':
        return 'XLRE'
    elif s == 'Consumer Staples':
        return 'XLP'
    elif s == 'Energy':
        return 'XLE'
    else:
        return None

def prep_spy_sectors():
    
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    file_name = 'spysectors'
    file_path = '../data/' + file_name + '.json'
    
    comps_df = pd.read_html(url)[0]
    comps_grp = comps_df.groupby('GICS Sector')

    res_list = []

    for k,v in comps_grp:

        comps_list = v[['Security', 'Symbol']].values.tolist()

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
            'Ticker': _set_sector(k),
            'Comps': sec_items
        }
        res_list.append(sec_dict)

        
    if res_list:
        with open(file_path, 'w') as fp:
            json.dump(res_list, fp)

        print('S&P 500 sectors data read was successfull.')

    else:
        raise ValueError("Failed to collect SPY sectors.")
            


if __name__ == '__main__':

    prep_spy_sectors()
