import logging
import logging.config
import os

# Directorio para logs
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'backend.log')

# Configuración del logging
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': LOG_FILE,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'level': 'DEBUG',
        }
    },
    'loggers': {
        '': {  # Logger raíz (captura todos los logs)
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'backend': {  # Logger específico
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

# Aplicar configuración
logging.config.dictConfig(LOGGING_CONFIG)

def get_logger(name):
    return logging.getLogger(f'backend.{name}')

""" Parte eliminada del código de configuración del logger 
'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_FILE,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'standard',
        },
"""