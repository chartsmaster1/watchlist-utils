# +
import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')
# -

url = 'https://en.wikipedia.org/wiki/Nasdaq-100'


# +
def read_prep_nasdaq(url):
    
    file_name = 'nasdaq'
    file_path = './data/' + file_name + '.json'
    
    try:
        comps = pd.read_html(url)[3]
        comps_list = comps[['Company', 'Ticker']].values.tolist()
        
        res_list = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Exchange': 'NASDAQ'
            }
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

    except Exception as e:
        logging.error(str(e))

read_prep_nasdaq(url)
# -


