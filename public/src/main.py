
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

# local scripts
import prep_nasdaq
import prep_sandp_sectors
import prep_companies_market_cap
import prep_coins_market_cap
import prep_etfs_market_cap
import prep_russell_1000
import prep_arkk
import prep_schd
import prep_qqq
import prep_russell_2000
import prep_spdr
import prep_berkshire


def main():
    # Market-cap data must exist before index preparers sort against it.
    # SPDR runs second so fresh spy.json/dia.json exist before the jobs
    # that enrich sectors from them (SCHD/QQQ/Russell 2000/Berkshire)
    # and before the sectors job, which is built from the sector SPDR lists.
    jobs = [
        ('companies', prep_companies_market_cap.read_prep_companies_market_cap),
        ('SPDR ETFs', prep_spdr.read_prep_spdr),
        ('nasdaq', prep_nasdaq.read_prep_nasdaq),
        ('ETFs', prep_etfs_market_cap.read_prep_etfs_market_cap),
        ('coins', prep_coins_market_cap.read_prep_coins),
        ('Russell 1000', prep_russell_1000.read_prep_russell),
        ('ARKK', prep_arkk.read_prep_arkk),
        ('SCHD', prep_schd.read_prep_schd),
        ('QQQ', prep_qqq.read_prep_qqq),
        ('Russell 2000', prep_russell_2000.read_prep_russell_2000),
        ('s&p sectors', prep_sandp_sectors.prep_spy_sectors),
        ('Berkshire Hathaway', prep_berkshire.read_prep_berkshire),
    ]
    failures = []
    for name, job in jobs:
        try:
            job()
        except Exception as e:
            print(f'{name} failed: {e}')
            failures.append(name)

    if failures:
        raise RuntimeError(f'Data refresh failed for: {", ".join(failures)}')

    write_manifest()


DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
MANIFEST_EXCLUDE = {'cusip_tickers.json', 'manifest.json'}


def count_rows(data):
    # Sector grouping file: rows are the holdings inside each sector.
    if isinstance(data, list):
        if data and all(isinstance(row, dict) and isinstance(row.get('Comps'), list) for row in data):
            return sum(len(row['Comps']) for row in data)
        return len(data)
    if isinstance(data, dict):
        return len(data)
    return None


def write_manifest():
    # Row counts + refresh date for the data-site index page.
    # Runs only after a fully successful refresh, so the manifest
    # always matches the committed data. Committed with the data
    # (the workflow does `git add public/data`).
    datasets = []
    for path in sorted(DATA_DIR.glob('*.json')):
        if path.name in MANIFEST_EXCLUDE:
            continue
        with path.open() as data_file:
            rows = count_rows(json.load(data_file))
        if rows is not None:
            datasets.append({'file': path.name, 'rows': rows})
    manifest = {
        'generatedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'datasets': datasets,
    }
    with (DATA_DIR / 'manifest.json').open('w') as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
    print(f'manifest.json: {len(datasets)} datasets')


if __name__ == '__main__':
    main()


# # save json files to frontend
# file_list = os.listdir('data/')

# for f in file_list:

#     try:
#         src_dir = os.path.join('data/', f)
#         des_dir = os.path.join('../frontend/src/data/', f)
#         shutil.copyfile(src_dir, des_dir)
#         print(f)

#     except Exception as e:
#         print(e)