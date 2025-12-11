from pathlib import Path
import sys
import os
import logging
import logging.config

from rich.logging import RichHandler
from rich.console import Console
from dotenv import dotenv_values, load_dotenv

# Configure UTF-8 encoding for Windows
if sys.platform == "win32":
    import locale
    # Set UTF-8 as default encoding for stdout/stderr when supported
    _stdout_reconf = getattr(sys.stdout, "reconfigure", None)
    if sys.stdout.encoding != 'utf-8' and callable(_stdout_reconf):
        _stdout_reconf(encoding='utf-8')
    _stderr_reconf = getattr(sys.stderr, "reconfigure", None)
    if sys.stderr.encoding != 'utf-8' and callable(_stderr_reconf):
        _stderr_reconf(encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent.absolute()
CONFIG_DIR = Path(BASE_DIR, "config")


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Point data directory to the project root level
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

ENV_VARIABLES = {
    **dotenv_values(BASE_DIR / ".env"),  # load environment variables from .env file
    **os.environ,  # load environment variables from the system
}

load_dotenv(BASE_DIR / ".env")

#Logger
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "minimal": {"format": "%(message)s"},
        "detailed": {
            "format": "%(levelname)s %(asctime)s [%(name)s:%(filename)s:%(funcName)s:%(lineno)d]\n%(message)s\n"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "minimal",
            "level": logging.DEBUG,
        },
        "info": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOGS_DIR, "info.log"),
            "maxBytes": 10485760,  # 1 MB
            "backupCount": 10,
            "formatter": "detailed",
            "level": logging.INFO,
            "encoding": "utf-8",
        },
        "error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOGS_DIR, "error.log"),
            "maxBytes": 10485760,  # 1 MB
            "backupCount": 10,
            "formatter": "detailed",
            "level": logging.ERROR,
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["console", "info", "error"],
        "level": logging.INFO,
        "propagate": True,
    },
    "loggers": {
        "default-logger": {
    "handlers": ["console", "info", "error"],
    "level": "INFO",
    "propagate": True,
},
        # Suppress verbose Azure SDK HTTP logging
        "azure.core.pipeline.policies.http_logging_policy": {
            "level": logging.WARNING,
        },
        # Suppress other Azure SDK loggers
        "azure": {
            "level": logging.WARNING,
        },
    },
}

logging.config.dictConfig(logging_config)
logger = logging.getLogger()

# Use Rich handler with wider console to prevent wrapping in Aspire dashboard
console = Console(width=200)
logger.handlers[0] = RichHandler(markup=True, console=console)
