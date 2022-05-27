# +
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import logging


logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

config = json.load(open('config.json'))

url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
parameters = {
  'start':'1',
  'limit':'100',
  'convert':'USD'
}
headers = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': config['CMC_API_KEY'],
}

session = Session()
session.headers.update(headers)

try:
    response = session.get(url, params=parameters)
    data = json.loads(response.text)
    coinlist = []
    for d in data['data']:
        try:
            if 'stablecoin' not in d['tags']:
                coinlist.append({
                    'Name': d['name'],
                    'Ticker': d['symbol'] + 'USD'
                })
                
        except:
            print(d)
    
except (ConnectionError, Timeout, TooManyRedirects) as e:
    logging.error(str(e))

if len(coinlist) > 0:
    try:
        file_path = './data/coins.json'
        with open(file_path, 'w') as fp:
            json.dump(coinlist, fp)

        print('CMC data read was successfull.')

    except Exception as e:
        logging.error(str(e))
        print('CMC data read failed.')

else:
    logging.error('read api return null.')
    print('CMC data read failed.')

