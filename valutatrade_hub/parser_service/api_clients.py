from abc import ABC, abstractmethod
import requests
from valutatrade_hub.core.exceptions import ApiRequestError
from .config import ParserConfig

class BaseApiClient(ABC):
    def __init__(self, config: ParserConfig):
        self.config = config

    @abstractmethod
    def fetch_rates(self) -> dict:
        pass

class CoinGeckoClient(BaseApiClient):
    def fetch_rates(self) -> dict:
        ids = ",".join(self.config.CRYPTO_ID_MAP.values())
        vs = self.config.BASE_CURRENCY.lower()
        url = f"{self.config.COINGECKO_URL}?ids={ids}&vs_currencies={vs}"
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            id_to_code = {v: k for k, v in self.config.CRYPTO_ID_MAP.items()}
            for coin_id, values in data.items():
                if coin_id in id_to_code:
                    code = id_to_code[coin_id]
                    rate = values.get(vs)
                    if rate:
                        rates[f"{code}_{self.config.BASE_CURRENCY}"] = rate
            return rates
        except requests.RequestException as e:
            raise ApiRequestError(f"CoinGecko network error: {e}")

class ExchangeRateApiClient(BaseApiClient):
    def fetch_rates(self) -> dict:
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("EXCHANGERATE_API_KEY не установлен. Фиатные курсы пропущены.")
        
        url = f"{self.config.EXCHANGERATE_API_URL}/{self.config.EXCHANGERATE_API_KEY}/latest/{self.config.BASE_CURRENCY}"
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            for currency in self.config.FIAT_CURRENCIES:
                rate = data.get("conversion_rates", {}).get(currency)
                if rate:
                    rates[f"{currency}_{self.config.BASE_CURRENCY}"] = 1.0 / rate
            return rates
        except requests.RequestException as e:
            raise ApiRequestError(f"ExchangeRate-API network error: {e}")