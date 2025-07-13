
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

            print('CMC data read was successfull.')

        except Exception as e:
            logging.error(str(e))
            print('CMC data read failed.')

    else:
        logging.error('read api return null.')
        print('CMC data read failed.')




if __name__ == '__main__':
    
    read_prep_coins()