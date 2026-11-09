from abc import ABC, abstractmethod
from .exceptions import CurrencyNotFoundError

class Currency(ABC):
    def __init__(self, code: str, name: str):
        if not (2 <= len(code) <= 5) or not code.isalpha():
            raise ValueError(f"Код валюты должен содержать от 2 до 5 букв: {code}")
        self.code = code.upper()
        self.name = name

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает форматированную информацию о валюте."""
        pass

class FiatCurrency(Currency):
    def __init__(self, code: str, name: str, issuing_country: str):
        super().__init__(code, name)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"

class CryptoCurrency(Currency):
    def __init__(self, code: str, name: str, algorithm: str, market_cap: float):
        super().__init__(code, name)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"

_REGISTRY = {
    "USD": FiatCurrency("USD", "US Dollar", "United States"),
    "EUR": FiatCurrency("EUR", "Euro", "Eurozone"),
    "RUB": FiatCurrency("RUB", "Russian Ruble", "Russia"),
    "BTC": CryptoCurrency("BTC", "Bitcoin", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("ETH", "Ethereum", "Ethash", 4.5e11)
}

def get_currency(code: str) -> Currency:
    code = code.upper()
    if code not in _REGISTRY:
        raise CurrencyNotFoundError(code)
    return _REGISTRY[code]