import json
import logging.config

from starlette.config import Config

config = Config()


DEBUG = config('DEBUG', cast=lambda b:  b=="true", default=True)

POKEPROXY_CONFIG: str = config('POKEPROXY_CONFIG', default=None)

POKESECRET_KEY: str = config('POKESECRET_KEY', default="default_secret")
if not POKEPROXY_CONFIG:
    raise Exception("POKEPROXY_CONFIG is not modified in the environment")
with open(POKEPROXY_CONFIG) as f:
    pokeproxy_config= json.load(f)


LOGGING = {
    "version": 1,
    "formatters": {
        "logger_name_prefix": {"()": "logging_formatters.ModuleNameFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG" if DEBUG else "INFO",
            "stream": "ext://sys.stdout",
            "formatter": "logger_name_prefix",
        },
    },
    "loggers": {
        "": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console"],
            "propagate": True,
        },
    }
}

logging.config.dictConfig(LOGGING)
