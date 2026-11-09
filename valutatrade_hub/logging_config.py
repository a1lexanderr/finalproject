import logging
from logging.handlers import RotatingFileHandler
import os
from valutatrade_hub.infra.settings import SettingsLoader

def setup_logging():
    settings = SettingsLoader()
    log_file = settings.get("LOG_FILE")
    
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger("valutatrade")
    logger.setLevel(settings.get("LOG_LEVEL"))
    
    if not logger.handlers:
        handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
        formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger