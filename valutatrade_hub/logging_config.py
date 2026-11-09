import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader

MAX_LOG_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

def setup_logging():
    settings = SettingsLoader()
    log_file = settings.get("LOG_FILE")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger("valutatrade")
    logger.setLevel(settings.get("LOG_LEVEL"))

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        formatter = logging.Formatter("%(levelname)s %(asctime)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
