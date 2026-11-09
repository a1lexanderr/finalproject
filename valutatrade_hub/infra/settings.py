import os
from pathlib import Path

class SettingsLoader:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.config = {
            "RATES_TTL_SECONDS": 300,
            "BASE_CURRENCY": "USD",
            "DATA_DIR": str(base_dir / "data"),
            "LOG_FILE": str(base_dir / "logs" / "actions.log"),
            "LOG_LEVEL": "INFO"
        }

    def get(self, key: str, default=None):
        return self.config.get(key, default)