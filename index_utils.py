import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

# read and save popular indecies

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

params_list = [
    {'url': 'https://en.wikipedia.org/wiki/Nasdaq-100', 'col': 'Ticker','path': 'nasdaq'},
    {'url': 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average', 'col': 'Symbol', 'path': 'dow'},
    {'url': 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 'col': 'Symbol', 'path': 'spy'},    
]

# read and save s&p sectors

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

def read_write_popIndex(params):
    
    url = params['url']
    col = params['col']
    path = params['path']
    file_path = './data/' + path + '.json'
    
    try:
        df_list = pd.read_html(url)

        df_out = None

        for dfx in df_list:
            if col in dfx.columns:
                df_out = dfx[[col]]
                df_out.columns = ['Symbol']

        if df_out is not None:
            res_list = list(df_out.Symbol.values)
            with open(file_path, "w") as write_file:
                json.dump(res_list, write_file)

        else:
            logging.error('failed to write data for ' + path)

    except Exception as e:
        logging.error(str(e))


for params in params_list:
    read_write_popIndex(params)


def prep_spy_sectors():
    
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    
    try:
        table_list = pd.read_html(url)

        table_out = None

        for tbl in table_list:
            if 'Symbol' in tbl.columns:
                table_out = tbl[['Symbol', 'GICS Sector']]
                table_out.columns = ['Symbol', 'GICS_Sector']
                table_out['Sector'] = [_set_sector(s) for s in table_out.GICS_Sector]

        if table_out is not None:
            res_dict = dict()
            sector_ids = list(table_out.Sector.unique())

            for idx in sector_ids:
                res_list = list(table_out[table_out.Sector == idx].Symbol.values)
                res_dict.update({idx: res_list})
                
            return res_dict

        else:
            return None
        
    except Exception as e:
        logging.error(str(e))
        return None


# +
try:
    res_out = prep_spy_sectors()

    if res_out is not None:
        file_path = './data/spysectors.json'
        with open(file_path, 'w') as fp:
            json.dump(res_out, fp)

    else:
        logging.error('failed to write data for spysectors.')
        
except Exception as e:
    logging.error(str(e))
