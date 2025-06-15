import logging
import logging.config

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
    },
    'loggers': {
        '': {  # Logger raíz
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'backend': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

# Aplicar configuración
logging.config.dictConfig(LOGGING_CONFIG)

def get_logger(name):
    return logging.getLogger(f'backend.{name}')
