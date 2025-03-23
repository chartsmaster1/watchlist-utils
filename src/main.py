
import os
import json
import shutil
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


try:
    prep_dow.read_prep_dow()

except Exception as e:
    print(e)


try:
    prep_nasdaq.read_prep_nasdaq()

except Exception as e:
    print(e)

    
try:
    prep_sandp.read_prep_sandp()

except Exception as e:
    print(e)


try:
    prep_sandp_sectors.prep_spy_sectors()

except Exception as e:
    print(e)


try:
    prep_companies_market_cap.read_prep_companies_market_cap()

except Exception as e:
    print(e)

# DOES NOT PRODUCE FILE OUTPUT *** SOURCE DATA UNDEFIND ***
try:
    prep_etfs_market_cap.read_prep_etfs()

except Exception as e:
    print(e)



try:
    prep_coins_market_cap.read_prep_coins()

except Exception as e:
    print(e)



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