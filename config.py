import os

class Config:
    # Database config.
    MONGODB_SETTINGS = {
        'db': 'infox_db',
        'host': '127.0.0.1',
        'port': 27017,
        'connect': False,
    }

    # LOCAL_DATA_PATH used for storing the raw data from crawling the github.
    LOCAL_DATA_PATH = os.environ.get('INFOX_LOCAL_DATA_PATH')

    # Overview page config.
    SHOW_NUMBER_FOR_PAGE = 6 # Project number per page in index page.

    # API_CALL_RETRY_TIMES = 5

    # Github Oauth Apps config.
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

    # secret key is a random string.
    SECRET_KEY = os.environ.get('INFOX_SECRET_KEY')

    # E-mail Config
    MAIL_SERVER = 'smtp.126.com'
    MAIL_PORT = 465
    MAIL_USERNAME = os.environ.get('INFOX_MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('INFOX_MAIL_PASSWORD')
    MAIL_USE_SSL = True
    FLASK_MAIL_SENDER = '<infox_help@126.com>'
    FLASK_MAIL_SUBJECT_PREFIX = '[INFOX(Forks-Insight)]'



class DevelopmentConfig(Config):
    DEBUG = True
    FORCED_UPDATING = True 
    RECRAWLER_MODE = True # Refresh will re-crawler the forks' info.

class ProductionConfig(Config):
    FORCED_UPDATING = True
    RECRAWLER_MODE = True # Refresh will re-crawler the forks' info.

config = {
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'default': DevelopmentConfig
}
