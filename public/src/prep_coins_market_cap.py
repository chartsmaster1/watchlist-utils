import pandas as pd
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import logging


logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

config = json.load(open('./config.json'))

url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
parameters = {
  'start':'1',
  'limit':'1000',
  'convert':'USD'
}
headers = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': config['CMC_API_KEY'],
}

session = Session()
session.headers.update(headers)

def _stable(d):
    if 'stablecoin' in d['tags']:
        return True
    else:
        return False

def _handle_ticker(tkr):
    if 'USD' in tkr:
        return tkr
    return tkr + 'USD'        


def read_prep_coins():

    coinlist = []
    try:
        response = session.get(url, params=parameters, verify=True)
        data = json.loads(response.text)
        for d in data['data']:
            try:
                coinlist.append({
                    'Rank': d['cmc_rank'],
                    'Name': d['name'],
                    'Ticker': _handle_ticker(d['symbol']),
                    'MarketCap': d['quote']['USD']['market_cap'],
                    'Stablecoin': _stable(d)
                })
                    
                    
            except Exception as e:
                print(e)
        
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        logging.error(str(e))

    if len(coinlist) > 0:
        try:
            file_path = '../data/coins.json'
            with open(file_path, 'w') as fp:
                json.dump(coinlist, fp)

            print('CMC data read and json write was successfull.')

            try:
                df = pd.read_json('../data/coins.json', dtype=str, encoding='utf-8')
                df['Rank'] = df['Rank'].astype(int)
                df['MarketCap'] = df['MarketCap'].astype(float)
                df.sort_values(by='Rank', inplace=True)
                df.to_csv('../data/coins.csv', index=False, encoding='utf-8-sig')
                print('CMC data read and csv write was successfull.')

            except Exception as e:
                logging.error(str(e))
                print('Failed to save CMC data to csv.')

        except Exception as e:
            logging.error(str(e))
            print('Failed to read & save CMC data.')

    else:
        logging.error('read api return null.')
        print('CMC data read failed.')


if __name__ == '__main__':
    
    read_prep_coins()