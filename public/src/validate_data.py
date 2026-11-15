"""Validate generated frontend data before it is committed or deployed."""

import csv
import json
import math
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
LIST_FILES = {
    'arkk.json': 'Ticker',
    'coins.json': 'Ticker',
    'etfs_market_cap.json': 'Ticker',
    'nasdaq.json': 'Ticker',
    'russell_1000.json': 'Ticker',
    'russell_2000.json': 'Ticker',
    'schd.json': 'Ticker',
    'qqq.json': 'Ticker',
    'spy.json': 'Ticker',
    'dia.json': 'Ticker',
    'mdy.json': 'Ticker',
    'spsm.json': 'Ticker',
    'berkshire.json': 'Ticker',
    'xlk.json': 'Ticker',
    'xlf.json': 'Ticker',
    'xlv.json': 'Ticker',
    'xle.json': 'Ticker',
    'xly.json': 'Ticker',
    'xlp.json': 'Ticker',
    'xli.json': 'Ticker',
    'xlb.json': 'Ticker',
    'xlre.json': 'Ticker',
    'xlu.json': 'Ticker',
    'xlc.json': 'Ticker',
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


def validate_etf_groups():
    """Validate etfgrouped.json + its CSV twin.

    Shape differs from the per-ticker list files (groups of tickers, with
    overlaps across groups expected), so it is checked separately and never
    added to LIST_FILES. If the files do not exist yet (first run, and the
    optional ETF groups job failed), warn and skip — the missing file must
    not block the rest of the refresh.
    """
    json_path = DATA_DIR / 'etfgrouped.json'
    csv_path = DATA_DIR / 'etfgrouped.csv'
    if not json_path.exists():
        print('etfgrouped.json: missing (ETF groups job did not produce it), skipping')
        return
    with json_path.open() as data_file:
        groups = json.load(data_file, parse_constant=reject_constant)
    if not isinstance(groups, list) or not groups:
        raise ValueError('etfgrouped.json must contain a non-empty list of groups')
    csv_rows = []
    for group in groups:
        if not isinstance(group, dict) or not group.get('Name') \
                or not isinstance(group.get('Items'), list) or not group['Items']:
            raise ValueError('etfgrouped.json has a group without a name or items')
        tickers = group['Items']
        if any(not t or not isinstance(t, str) or t == 'nan' for t in tickers):
            raise ValueError(f"etfgrouped.json group {group['Name']} has a blank ticker")
        if len(tickers) != len(set(tickers)):
            raise ValueError(f"etfgrouped.json group {group['Name']} has duplicate tickers")
        csv_rows += [(group['Name'], t) for t in tickers]
    if not csv_path.exists():
        raise ValueError('etfgrouped.json exists but etfgrouped.csv is missing')
    with csv_path.open(newline='') as data_file:
        rows = list(csv.DictReader(data_file))
    if [(r['Group'], r['Ticker']) for r in rows] != csv_rows:
        raise ValueError('etfgrouped.csv does not match etfgrouped.json')
    print(f"etfgrouped.json: {len(groups)} groups, {len(csv_rows)} tickers (CSV: {len(rows)})")


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
    validate_etf_groups()


if __name__ == '__main__':
    main()