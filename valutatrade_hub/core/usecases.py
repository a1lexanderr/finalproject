import hashlib
import uuid
from datetime import datetime, timedelta

from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import SettingsLoader

from .currencies import get_currency
from .exceptions import ApiRequestError
from .models import Portfolio, User
from .utils import PORTFOLIOS_FILE, RATES_FILE, USERS_FILE, load_json, save_json

current_session = {"user_id": None}

settings = SettingsLoader()


def get_current_user_id():
    return current_session["user_id"]


def require_login():
    if current_session["user_id"] is None:
        raise PermissionError("Сначала выполните login.")


@log_action("REGISTER")
def register_user(username: str, password: str) -> User:
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов.")
    if not username.strip():
        raise ValueError("Имя пользователя не может быть пустым.")

    users_data = load_json(USERS_FILE, [])
    for u in users_data:
        if u["username"] == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято.")

    new_user_id = 1 if not users_data else max(u["user_id"] for u in users_data) + 1
    salt = uuid.uuid4().hex
    hashed_password = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    new_user = User(
        user_id=new_user_id,
        username=username,
        hashed_password=hashed_password,
        salt=salt,
    )

    users_data.append(
        {
            "user_id": new_user.user_id,
            "username": new_user.username,
            "hashed_password": new_user.hashed_password,
            "salt": new_user.salt,
            "registration_date": new_user.registration_date.isoformat(),
        }
    )
    save_json(USERS_FILE, users_data)

    portfolios_data = load_json(PORTFOLIOS_FILE, [])
    portfolios_data.append({"user_id": new_user.user_id, "wallets": {}})
    save_json(PORTFOLIOS_FILE, portfolios_data)

    return new_user


@log_action("LOGIN")
def login_user(username: str, password: str) -> User:
    users_data = load_json(USERS_FILE, [])
    user_dict = next((u for u in users_data if u["username"] == username), None)

    if not user_dict:
        raise ValueError(f"Пользователь '{username}' не найден.")

    user = User(
        user_id=user_dict["user_id"],
        username=user_dict["username"],
        hashed_password=user_dict["hashed_password"],
        salt=user_dict["salt"],
        registration_date=user_dict["registration_date"],
    )

    if not user.verify_password(password):
        raise ValueError("Неверный пароль.")

    current_session["user_id"] = user.user_id
    return user


def get_all_rates() -> dict:
    rates_data = load_json(RATES_FILE, {"pairs": {}, "last_refresh": None})
    now = datetime.now()
    ttl = settings.get("RATES_TTL_SECONDS", 300)

    need_update = True
    if rates_data.get("last_refresh"):
        last_refresh = datetime.fromisoformat(
            rates_data["last_refresh"].replace("Z", "")
        )
        if now - last_refresh < timedelta(seconds=ttl):
            need_update = False

    if need_update:
        try:
            from valutatrade_hub.parser_service.updater import RatesUpdater

            updater = RatesUpdater()
            updater.run_update()
            rates_data = load_json(RATES_FILE, {"pairs": {}, "last_refresh": None})
        except Exception as e:
            raise ApiRequestError(str(e))

    return rates_data.get("pairs", {})


def get_exchange_rate(from_currency: str, to_currency: str) -> tuple[float, str]:
    from_curr = get_currency(from_currency)
    to_curr = get_currency(to_currency)

    if from_curr.code == to_curr.code:
        return 1.0, datetime.now().isoformat()

    pairs = get_all_rates()

    pair = f"{from_curr.code}_{to_curr.code}"
    if pair in pairs:
        return pairs[pair]["rate"], pairs[pair]["updated_at"]

    reverse_pair = f"{to_curr.code}_{from_curr.code}"
    if reverse_pair in pairs:
        return 1.0 / pairs[reverse_pair]["rate"], pairs[reverse_pair]["updated_at"]

    raise ApiRequestError(f"Курс {from_curr.code}→{to_curr.code} недоступен в кеше.")


def _get_user_portfolio_model() -> Portfolio:
    require_login()
    user_id = current_session["user_id"]
    portfolios_data = load_json(PORTFOLIOS_FILE, [])

    for p_data in portfolios_data:
        if p_data["user_id"] == user_id:
            return Portfolio(user_id=user_id, wallets_data=p_data.get("wallets", {}))
    return Portfolio(user_id=user_id)


def _save_user_portfolio_model(portfolio: Portfolio):
    portfolios_data = load_json(PORTFOLIOS_FILE, [])
    wallets_dict = {
        code: {"currency_code": code, "balance": wallet.balance}
        for code, wallet in portfolio.wallets.items()
    }

    updated = False
    for i, p_data in enumerate(portfolios_data):
        if p_data["user_id"] == portfolio.user_id:
            portfolios_data[i]["wallets"] = wallets_dict
            updated = True
            break

    if not updated:
        portfolios_data.append({"user_id": portfolio.user_id, "wallets": wallets_dict})

    save_json(PORTFOLIOS_FILE, portfolios_data)


def get_portfolio_info(base_currency: str = "USD") -> dict:
    base_curr = get_currency(base_currency)  # Проверка базы
    portfolio = _get_user_portfolio_model()
    rates = get_all_rates()

    total_value = portfolio.get_total_value(rates, base_curr.code)

    wallets_info = []
    for code, wallet in portfolio.wallets.items():
        rate, _ = get_exchange_rate(code, base_curr.code)
        wallets_info.append(
            {
                "currency": code,
                "balance": wallet.balance,
                "value_in_base": wallet.balance * rate,
            }
        )

    return {
        "base_currency": base_curr.code,
        "total_value": total_value,
        "wallets": wallets_info,
    }


@log_action("BUY")
def buy_currency(currency_code: str, amount: float) -> dict:
    curr = get_currency(currency_code)
    if curr.code == "USD":
        raise ValueError("Нельзя купить USD за USD.")

    portfolio = _get_user_portfolio_model()
    rate, _ = get_exchange_rate(curr.code, "USD")
    cost_in_usd = amount * rate

    try:
        usd_wallet = portfolio.get_wallet("USD")
    except KeyError:
        raise ValueError(
            "У вас нет USD-кошелька или на нем 0. Сначала пополните баланс."
        )

    usd_wallet.withdraw(cost_in_usd)

    try:
        target_wallet = portfolio.get_wallet(curr.code)
    except KeyError:
        portfolio.add_currency(curr.code)
        target_wallet = portfolio.get_wallet(curr.code)

    target_wallet.deposit(amount)
    _save_user_portfolio_model(portfolio)

    return {
        "currency": curr.code,
        "amount": amount,
        "rate": rate,
        "cost": cost_in_usd,
        "new_balance": target_wallet.balance,
    }


@log_action("SELL")
def sell_currency(currency_code: str, amount: float) -> dict:
    curr = get_currency(currency_code)
    if curr.code == "USD":
        raise ValueError("Нельзя продать USD за USD.")

    portfolio = _get_user_portfolio_model()

    try:
        wallet = portfolio.get_wallet(curr.code)
    except KeyError:
        raise ValueError(f"У вас нет кошелька '{curr.code}'.")

    wallet.withdraw(amount)

    rate, _ = get_exchange_rate(curr.code, "USD")
    revenue_in_usd = amount * rate

    try:
        usd_wallet = portfolio.get_wallet("USD")
    except KeyError:
        portfolio.add_currency("USD")
        usd_wallet = portfolio.get_wallet("USD")

    usd_wallet.deposit(revenue_in_usd)
    _save_user_portfolio_model(portfolio)

    return {
        "currency": curr.code,
        "amount": amount,
        "rate": rate,
        "revenue": revenue_in_usd,
        "new_balance": wallet.balance,
    }


@log_action("ADD_FIAT")
def add_fiat_usd(amount: float) -> float:
    if amount <= 0:
        raise ValueError("Сумма пополнения должна быть больше нуля.")

    portfolio = _get_user_portfolio_model()
    try:
        usd_wallet = portfolio.get_wallet("USD")
    except KeyError:
        portfolio.add_currency("USD")
        usd_wallet = portfolio.get_wallet("USD")

    usd_wallet.deposit(amount)
    _save_user_portfolio_model(portfolio)
    return usd_wallet.balance
