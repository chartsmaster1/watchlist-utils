
# +
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
parameters = {
  'start':'1',
  'limit':'100',
  'convert':'USD'
}
headers = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': 'YOUR-CMC-API-KEY',
}

session = Session()
session.headers.update(headers)

try:
    response = session.get(url, params=parameters)
    data = json.loads(response.text)
    coinlist = [d['symbol']+'USD' for d in data['data']]
    
except (ConnectionError, Timeout, TooManyRedirects) as e:
    logging.error(str(e))

if len(coinlist) > 0:
    try:
        file_path = './data/coins.json'
        with open(file_path, 'w') as fp:
            json.dump(coinlist, fp)

    except Exception as e:
        logging.error(str(e))

else:
    logging.error('read api return null.')