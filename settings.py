import logging
import tornado
import tornado.template
import os
from tornado.options import define, options
import logconfig

# Make filepaths relative to settings.
path = lambda root, *a: os.path.join(root, *a)
ROOT = os.path.dirname(os.path.abspath(__file__))

define("host", default="localhost", help="app host", type=str)
define("port", default=8888, help="run on the given port", type=int)
define("config", default=None, help="tornado config file")
define("debug", default=False, help="debug mode")
tornado.options.parse_command_line()

STATIC_ROOT = path(ROOT, 'static')
TEMPLATE_ROOT = path(ROOT, 'templates')


# Deployment Configuration

class DeploymentType:
    PRODUCTION = "PRODUCTION"
    DEV = "DEV"
    SOLO = "SOLO"
    STAGING = "STAGING"
    dict = {
        SOLO: 1,
        PRODUCTION: 2,
        DEV: 3,
        STAGING: 4
    }


if 'DEPLOYMENT_TYPE' in os.environ:
    DEPLOYMENT = os.environ['DEPLOYMENT_TYPE'].upper()
else:
    DEPLOYMENT = DeploymentType.SOLO

settings = {}
settings['debug'] = DEPLOYMENT != DeploymentType.PRODUCTION or options.debug
settings['static_path'] = STATIC_ROOT
settings['cookie_secret'] = "your-cookie-secret"
settings['xsrf_cookies'] = False  # TODO: Might need to change this to True later
settings['template_loader'] = tornado.template.Loader(TEMPLATE_ROOT)

# Security
settings['JWT_SECRET'] = "secret"  # TODO: Secret should be different for every User
settings['JWT_ALGORITHM'] = "HS256"

# MySQL Database settings
settings['DB_LOCATION'] = "production"  # values: ["local", "production"]
settings['DB_ENGINE_ORM_MAP'] = {'mysql': "mysql"}
settings['DB_ENGINE'] = "mysql"
settings['DB_HOST'] = "localhost" if settings['DB_LOCATION'] == "local" else "production-server.com"
settings['DB_PORT'] = 3306
settings['DB_USER'] = "local-user" if settings['DB_LOCATION'] == "local" else "production-user"
settings['DB_PASSWORD'] = "local-password" if settings['DB_LOCATION'] == "local" else "production-password"
settings['DB_SCHEMA'] = "local-schema" if settings['DB_LOCATION'] == "local" else "production-schema"

# Static file settings
settings['FILE_EXPORT_PATH'] = "static/exportfiles"  # Relative path where export files will be stored
settings['FILE_DELETE_INTERVAL_HOURS'] = 1  # Interval to run delete file export scheduled task
settings['FILE_EXPORT_LIFETIME_HOURS'] = 1  # Number of hours export files can last in the system

# Formatting
settings['DATE_DISPLAY_FORMAT'] = "%Y-%m-%d"
settings['DATETIME_DISPLAY_FORMAT'] = "%Y-%m-%d %H:%M:%S"

# Purchases
COIN_PRICES = {5: 250,
               20:1000,
               100:4500,
               150:5000,
               200:8000,
               300:9000}
settings['COIN_PRICES'] = COIN_PRICES

# Logging
SYSLOG_TAG = "artmego"
SYSLOG_FACILITY = logging.handlers.SysLogHandler.LOG_LOCAL2

# See PEP 391 and logconfig for formatting help.  Each section of LOGGERS
# will get merged into the corresponding section of log_settings.py.
# Handlers and log levels are set up automatically based on LOG_LEVEL and DEBUG
# unless you set them here.  Messages will not propagate through a logger
# unless propagate: True is set.
LOGGERS = {
    'loggers': {
        'artmego': {},
    },
}

if settings['debug']:
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO
USE_SYSLOG = DEPLOYMENT != DeploymentType.SOLO

logconfig.initialize_logging(SYSLOG_TAG, SYSLOG_FACILITY, LOGGERS,
                             LOG_LEVEL, USE_SYSLOG)

if options.config:
    tornado.options.parse_config_file(options.config)
