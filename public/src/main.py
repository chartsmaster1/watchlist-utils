
import logging
logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

# local scripts
import prep_dow
import prep_nasdaq
import prep_sandp
import prep_sandp_sectors
import prep_companies_market_cap
import prep_coins_market_cap
import prep_etfs_market_cap
import prep_russell_1000
import prep_arkk


def main():
    # Market-cap data must exist before index preparers sort against it.
    jobs = [
        ('companies', prep_companies_market_cap.read_prep_companies_market_cap),
        ('dow', prep_dow.read_prep_dow),
        ('nasdaq', prep_nasdaq.read_prep_nasdaq),
        ('s&p 500', prep_sandp.read_prep_sandp),
        ('s&p sectors', prep_sandp_sectors.prep_spy_sectors),
        ('ETFs', prep_etfs_market_cap.read_prep_etfs_market_cap),
        ('coins', prep_coins_market_cap.read_prep_coins),
        ('Russell 1000', prep_russell_1000.read_prep_russell),
        ('ARKK', prep_arkk.read_prep_arkk),
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