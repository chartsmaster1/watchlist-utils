import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')
# logging.warning('This will get logged to a file')
logging.error('This will get logged to a file')


