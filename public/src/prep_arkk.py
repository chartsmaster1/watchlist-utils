# source: https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv
# rename to "arkk_holdings.csv"
# Manually download, rename, and move to data directory.



import json
import pandas as pd
import logging
import requests
from io import StringIO
from pathlib import Path

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

SOURCE_URL = 'https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv'
REQUIRED_COLUMNS = {'company', 'ticker', 'weight (%)'}


def read_prep_arkk(download=True):
    
    file_name = 'arkk'
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_path = data_dir / (file_name + '.json')
    holdings_path = data_dir / 'arkk_holdings.csv'

    try:
        if download:
            response = requests.get(
                SOURCE_URL,
                headers={'User-Agent': 'watchlist-utils/1.0'},
                timeout=30,
            )
            response.raise_for_status()
            df_raw = pd.read_csv(StringIO(response.text))
            missing_columns = REQUIRED_COLUMNS - set(df_raw.columns)
            if missing_columns:
                raise ValueError(f'ARKK source missing columns: {sorted(missing_columns)}')
            if df_raw['ticker'].notna().sum() == 0:
                raise ValueError('ARKK source contains no holdings')
            temporary_path = holdings_path.with_suffix('.csv.tmp')
            normalized_csv = response.text.replace('\r\n', '\n').replace('\r', '\n')
            temporary_path.write_text(normalized_csv)
            temporary_path.replace(holdings_path)
        else:
            df_raw = pd.read_csv(holdings_path)

        df_raw = df_raw.dropna(subset=['ticker']).reset_index(drop=True)
        missing_columns = REQUIRED_COLUMNS - set(df_raw.columns)
        if missing_columns:
            raise ValueError(f'ARKK file missing columns: {sorted(missing_columns)}')
        df_raw['ticker'] = df_raw['ticker'].str.strip().str.upper()
        df_raw['ticker'] = df_raw['ticker'].apply(lambda x: x.split(' ')[0] if ' ' in x else x)

        res_list = []
        for idx, row in df_raw.iterrows():
            weight = float(str(row['weight (%)']).replace('%', '').strip())
            d = {
                'Rank': int(idx)+ 1,
                'Name': row['company'],
                'Ticker': row['ticker'],
                'Weight': round(weight, 2),}
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        # Save to CSV
        try:
            df = pd.read_json(file_path)
            df.to_csv(data_dir / f'{file_name}.csv', index=False, encoding='utf-8-sig')
            print('ARKK data read and csv write was successfull.')

        except Exception as e:
            logging.error(str(e))
            print('Failed to save ARKK data to csv.')

    except Exception as e:
        logging.error(str(e))
        print(f'ARKK data read failed. {e}')



if __name__ == '__main__':

    read_prep_arkk()