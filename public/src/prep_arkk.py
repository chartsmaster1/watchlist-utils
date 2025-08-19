# source: https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv
# rename to "arkk_holdings.csv"
# Manually download, rename, and move to data directory.



import json
import pandas as pd
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def read_prep_arkk():
    
    file_name = 'arkk'
    file_path = '../data/' + file_name + '.json'

    try:
        df_raw = pd.read_csv('../data/arkk_holdings.csv').dropna(subset=['ticker']).reset_index(drop=True)

        res_list = []
        for idx, row in df_raw.iterrows():
            d = {
                'Rank': int(idx)+ 1,
                'Name': row['company'],
                'Ticker': row['ticker'],
                'Weight': round(float(row['weight (%)'].replace('%', '').strip()), 2),}
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        # Save to CSV
        try:
            df = pd.read_json(file_path)
            df.to_csv(f'../data/{file_name}.csv', index=False, encoding='utf-8-sig')
            print('ARKK data read and csv write was successfull.')

        except Exception as e:
            logging.error(str(e))
            print('Failed to save ARKK data to csv.')

    except Exception as e:
        logging.error(str(e))
        print(f'ARKK data read failed. {e}')



if __name__ == '__main__':

    read_prep_arkk()