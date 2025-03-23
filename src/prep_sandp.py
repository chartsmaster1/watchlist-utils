
import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def read_prep_sandp():
    
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    file_name = 'spy'
    file_path = '../data/' + file_name + '.json'
    
    try:
        comps = pd.read_html(url)[0]
        comps_list = comps[['Security', 'Symbol']].values.tolist()
        
        res_list = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Exchange': ''
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