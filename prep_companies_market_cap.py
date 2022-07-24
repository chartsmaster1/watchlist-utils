# Manually download, rename, and move "CompaniesMarketCap.csv" from https://companiesmarketcap.com/ to "data" folder.

# +
import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


# +
def read_prep_companies_market_cap():
    
    df = pd.read_csv('./data/CompaniesMarketCap.csv').sort_values('Rank')
    
    file_name = 'stocks'
    file_path = './data/' + file_name + '.json'
    
    try:
        info_list = df.values.tolist()
        
        res_list = []
        for item in info_list:
            d = {
                'Rank': item[0],
                'Name': item[1],
                'Ticker': item[2],
                'MarketCap': item[3],
            }
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('Companies market cap data read was successfull.')

    except Exception as e:
        logging.error(str(e))
        print('Companies market cap data read failed.')

read_prep_companies_market_cap()
