import hashlib
from datetime import datetime
from typing import Dict

from .exceptions import InsufficientFundsError

MIN_PASSWORD_LENGTH = 4

class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: str = None,
    ):
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt

        if registration_date:
            self._registration_date = datetime.fromisoformat(registration_date)
        else:
            self._registration_date = datetime.now()

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        if not value or not str(value).strip():
            raise ValueError("Имя пользователя не может быть пустым.")
        self._username = str(value).strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> str:
        date_str = self._registration_date.strftime("%Y-%m-%d %H:%M:%S")
        return f"ID: {self._user_id} | Username: {self._username} | Зарегистрирован: {date_str}"

    def change_password(self, new_password: str):
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValueError("Пароль должен быть не короче 4 символов.")
        self._hashed_password = self._generate_hash(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        return self._hashed_password == self._generate_hash(password, self._salt)

    @staticmethod
    def _generate_hash(password: str, salt: str) -> str:
        """Вспомогательный приватный метод для генерации хеша"""
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = str(currency_code).upper()
        self.balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        if not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом.")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным.")
        self._balance = float(value)

    def deposit(self, amount: float):
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError(
                "Сумма пополнения ('amount') должна быть положительным числом."
            )
        self.balance += amount

    def withdraw(self, amount: float):
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError(
                "Сумма снятия ('amount') должна быть положительным числом."
            )
        if amount > self.balance:
            raise InsufficientFundsError(
                available=self.balance, required=amount, code=self.currency_code
            )
        self.balance -= amount

    def get_balance_info(self) -> str:
        return f"{self.currency_code}: {self.balance:.4f}"


class Portfolio:
    def __init__(self, user_id: int, wallets_data: dict = None):
        self._user_id = user_id
        self._wallets: Dict[str, Wallet] = {}

        if wallets_data:
            for curr_code, w_data in wallets_data.items():
                self._wallets[curr_code.upper()] = Wallet(
                    currency_code=w_data.get("currency_code", curr_code),
                    balance=w_data.get("balance", 0.0),
                )

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str):
        currency_code = str(currency_code).upper()
        if currency_code in self._wallets:
            raise ValueError(f"Кошелек для валюты '{currency_code}' уже существует.")
        self._wallets[currency_code] = Wallet(currency_code=currency_code)

    def get_wallet(self, currency_code: str) -> Wallet:
        currency_code = str(currency_code).upper()
        if currency_code not in self._wallets:
            raise KeyError(f"У вас нет кошелька '{currency_code}'.")
        return self._wallets[currency_code]

    def get_total_value(
        self, exchange_rates: dict, base_currency: str = "USD"
    ) -> float:
        """
        exchange_rates - словарь с курсами, который будет передаваться из бизнес-логики (usecases.py).
        Пример: {"BTC_USD": {"rate": 59337.21}, "EUR_USD": {"rate": 1.0786}}
        """
        total = 0.0
        base_currency = base_currency.upper()

        for curr, wallet in self._wallets.items():
            if curr == base_currency:
                total += wallet.balance
            else:
                pair = f"{curr}_{base_currency}"
                if pair in exchange_rates:
                    rate = exchange_rates[pair]["rate"]
                    total += wallet.balance * rate
                else:
                    reverse_pair = f"{base_currency}_{curr}"
                    if reverse_pair in exchange_rates:
                        rate = 1 / exchange_rates[reverse_pair]["rate"]
                        total += wallet.balance * rate
                    else:
                        raise ValueError(
                            f"Не удалось получить курс для {curr}→{base_currency}"
                        )
        return total
