import logging
import logging.config
from logging.handlers import RotatingFileHandler
import os

# Configuración base
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'backend.log')
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]'

# Crear directorio de logs si no existe
os.makedirs(LOG_DIR, exist_ok=True)

# Configuración del logging
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': LOG_FORMAT,
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_FILE,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'backend': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    }
}

# Aplicar configuración
logging.config.dictConfig(LOGGING_CONFIG)

def get_logger(name):
    return logging.getLogger(f'backend.{name}')
