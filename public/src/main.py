
import logging
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
    # and before the sectors job, which is derived from spy.json.
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