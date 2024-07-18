import logging
import logging.config
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os
from datetime import datetime

# Define the directory for log files
LOG_DIR = Path(__file__).parent.parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# Define the log file name with the current date
LOG_FILE = LOG_DIR / f"app_{datetime.now().strftime('%Y-%m-%d')}.log"
ERROR_LOG_FILE = LOG_DIR / 'errors.log'

# Environment variables for log level configuration
CONSOLE_LOG_LEVEL = os.getenv('LOG_LEVEL_CONSOLE', 'DEBUG')
FILE_LOG_LEVEL = os.getenv('LOG_LEVEL_FILE', 'DEBUG')

# Define the logging configuration dictionary
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': CONSOLE_LOG_LEVEL,
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_FILE,
            'formatter': 'detailed',
            'level': FILE_LOG_LEVEL,
            'maxBytes': 512 * 1024 * 1024,  # 512MB
            'backupCount': 5,
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': ERROR_LOG_FILE,
            'formatter': 'detailed',
            'level': 'ERROR',
            'maxBytes': 512 * 1024 * 1024,  # 512MB
            'backupCount': 5,
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

def setup_logging():
    """
    Setup logging configuration using the defined configuration dictionary.
    
    This function sets up logging with the following features:
    - Console logging with the level defined by the LOG_LEVEL_CONSOLE environment variable.
    - File logging with the level defined by the LOG_LEVEL_FILE environment variable.
    - Error file logging for messages with level ERROR and above.
    - Rotating log files to manage log file size and keep backups.
    
    Note:
    - The log file size is set to 512MB with up to 5 backup files.
    - Email logging configuration is removed as it was not required by the issue.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
