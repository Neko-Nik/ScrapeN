"""
This file contains Global constants
Also storing all the env and config variables here
"""

from src.utils.base.libraries import os, configparser, dotenv

# load env variables
dotenv.load_dotenv()

# environment variables
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SIGNING_SECRET = os.getenv("STRIPE_WEBHOOK_SIGNING_SECRET")


# config.cfg file setup
config = configparser.ConfigParser()
CONFIG_FILE_PATH = os.path.join(os.getcwd(), 'config.cfg')
config.read(CONFIG_FILE_PATH)
## Main config data
log_config_data = config['log']
scraping_config_data = config['scraping']


# config.cfg file variables

## log variables
LOG_LEVEL = int( log_config_data.get('LOG_LEVEL', 40 ) )
LOG_FILE_PATH = log_config_data.get('LOG_FILE_PATH', 'logs/log.txt' )
NUMBER_OF_LOGS_TO_DISPLAY = int( log_config_data.get('NUMBER_OF_LOGS_TO_DISPLAY', 100 ) )


## scraping variables
LIST_OF_SKIP_CODES = scraping_config_data.get('LIST_OF_SKIP_CODES', '404,500' ).split(',')
OUTPUT_ROOT_DIR = scraping_config_data.get('OUTPUT_ROOT_DIR', 'output_files' )

# Other constants

## Error messages
ERROR_MESSAGES = {
    403: "Please Pass correct Token For Authentication",
    401: "Please Pass Token For Authentication",
    404: "Resource Not Found",
    500: "Internal Server Error",
    400: "Bad Request, please check the query",
    412: "Please pass the required entities"
}
