import json
import os
from tempfile import NamedTemporaryFile

from valutatrade_hub.core.utils import load_json

from .config import ParserConfig


class StorageManager:
    def __init__(self, config: ParserConfig):
        self.config = config
        self.config.RATES_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    def save_rates(self, pairs_data: dict):
        self._atomic_write(self.config.RATES_FILE_PATH, pairs_data)

    def append_history(self, history_records: list):
        existing = load_json(self.config.HISTORY_FILE_PATH, [])
        existing.extend(history_records)
        self._atomic_write(self.config.HISTORY_FILE_PATH, existing)

    def _atomic_write(self, filepath, data):
        dirpath = filepath.parent
        with NamedTemporaryFile("w", dir=dirpath, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, indent=4, ensure_ascii=False)
            tempname = tf.name
        os.replace(tempname, filepath)
