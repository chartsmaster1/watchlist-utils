
import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def read_prep_nasdaq():
    
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    file_name = 'nasdaq'
    file_path = '../data/' + file_name + '.json'
    
    try:
        comps = pd.read_html(url)[4]
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

        print('Nasdaq data read was successfull.')

    except Exception as e:
        logging.error(str(e))
        print(f'Nasdaq data read failed. {e}')


if __name__ == '__main__':

    read_prep_nasdaq()

