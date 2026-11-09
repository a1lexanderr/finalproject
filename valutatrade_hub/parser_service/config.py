import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Ищем и загружаем переменные из файла .env в корне проекта
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

@dataclass
class ParserConfig:
    EXCHANGERATE_API_KEY: str = os.environ.get("EXCHANGERATE_API_KEY", "")

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    })

    RATES_FILE_PATH: Path = BASE_DIR / "data" / "rates.json"
    HISTORY_FILE_PATH: Path = BASE_DIR / "data" / "exchange_rates.json"
    
    REQUEST_TIMEOUT: int = 10