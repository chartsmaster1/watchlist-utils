"""Validate generated frontend data before it is committed or deployed."""

import csv
import json
import math
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
LIST_FILES = {
    'arkk.json': 'Ticker',
    'coins.json': 'Ticker',
    'dow.json': 'Ticker',
    'etfs_market_cap.json': 'Ticker',
    'nasdaq.json': 'Ticker',
    'russell_1000.json': 'Ticker',
    's&p500.json': 'Ticker',
    'stocks.json': 'Ticker',
    'spysectors.json': 'Ticker',
}


def reject_constant(value):
    raise ValueError(f'non-standard JSON constant: {value}')


def validate_json(filename, ticker_field):
    with (DATA_DIR / filename).open() as data_file:
        data = json.load(data_file, parse_constant=reject_constant)
    if not isinstance(data, list) or not data:
        raise ValueError(f'{filename} must contain a non-empty list')
    tickers = [row.get(ticker_field) for row in data if isinstance(row, dict)]
    if len(tickers) != len(data) or any(not ticker or ticker == 'nan' for ticker in tickers):
        raise ValueError(f'{filename} contains a blank ticker')
    if filename not in {'coins.json', 'spysectors.json'} and len(tickers) != len(set(tickers)):
        raise ValueError(f'{filename} contains duplicate tickers')
    for row in data:
        for value in row.values():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f'{filename} contains a non-finite number')
    return len(data)


def validate_csv(filename):
    with (DATA_DIR / filename).open(newline='') as data_file:
        rows = list(csv.DictReader(data_file))
    if not rows:
        raise ValueError(f'{filename} must contain records')
    return len(rows)


def main():
    for filename, ticker_field in LIST_FILES.items():
        count = validate_json(filename, ticker_field)
        csv_name = 'CompaniesMarketCap.csv' if filename == 'stocks.json' else filename.replace('.json', '.csv')
        csv_count = validate_csv(csv_name)
        counts_match = count == csv_count
        if filename == 'stocks.json':
            counts_match = csv_count >= count
        if filename not in {'spysectors.json'} and not counts_match:
            raise ValueError(f'{filename} has {count} rows but {csv_name} has {csv_count}')
        print(f'{filename}: {count} records (CSV: {csv_count})')


if __name__ == '__main__':
    main()