
import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def read_prep_russell():

    url = 'https://en.wikipedia.org/wiki/Russell_1000_Index'
    
    file_name = 'russell_1000'
    file_path = '../data/' + file_name + '.json'
    
    try:
        comps = pd.read_html(url)[3]
        comps_list = comps[['Company', 'Symbol', 'GICS Sector']].values.tolist()
        
        res_list = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Sector': item[2]
            }
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('Russell 1000 data read was successfull.')

    except Exception as e:
        logging.error(str(e))
        print(f'Russell 1000 data read failed. {e}')


if __name__ == '__main__':

    read_prep_russell()