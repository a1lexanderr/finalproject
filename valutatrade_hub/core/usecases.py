import random
import uuid
import hashlib
from datetime import datetime, timedelta
from .utils import load_json, save_json, USERS_FILE, PORTFOLIOS_FILE, RATES_FILE
from .models import User, Portfolio

current_session = {
    "user_id": None
}

def register_user(username: str, password: str) -> User:
    """
    Регистрирует нового пользователя: проверяет уникальность, хеширует пароль,
    сохраняет в JSON и создает пустой портфель.
    """
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
    hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    
    new_user = User(
        user_id=new_user_id,
        username=username,
        hashed_password=hashed_password,
        salt=salt
    )
    
    user_dict = {
        "user_id": new_user.user_id,
        "username": new_user.username,
        "hashed_password": new_user.hashed_password,
        "salt": new_user.salt,
        "registration_date": new_user.registration_date.isoformat()
    }
    users_data.append(user_dict)
    save_json(USERS_FILE, users_data)
    
    portfolios_data = load_json(PORTFOLIOS_FILE, [])
    portfolios_data.append({
        "user_id": new_user.user_id,
        "wallets": {}
    })
    save_json(PORTFOLIOS_FILE, portfolios_data)
    
    return new_user

def login_user(username: str, password: str) -> User:
    """
    Ищет пользователя по имени, проверяет пароль. 
    Если успех - сохраняет ID в текущую сессию.
    """
    users_data = load_json(USERS_FILE, [])
    
    user_dict = None
    for u in users_data:
        if u["username"] == username:
            user_dict = u
            break
            
    if not user_dict:
        raise ValueError(f"Пользователь '{username}' не найден.")
        
    user = User(
        user_id=user_dict["user_id"],
        username=user_dict["username"],
        hashed_password=user_dict["hashed_password"],
        salt=user_dict["salt"],
        registration_date=user_dict["registration_date"]
    )
    
    if not user.verify_password(password):
        raise ValueError("Неверный пароль.")
        
    current_session["user_id"] = user.user_id
    
    return user

def get_current_user_id():
    """Возвращает ID текущего пользователя или None"""
    return current_session["user_id"]

def require_login():
    """Вспомогательная функция для проверки авторизации в других командах"""
    if current_session["user_id"] is None:
        raise PermissionError("Сначала выполните login.")

def get_all_rates() -> dict:
    """Получает курсы валют из кеша. Если устарели (> 5 мин) - обновляет."""
    rates = load_json(RATES_FILE, {})
    now = datetime.now()

    need_update = True
    if "last_refresh" in rates:
        last_refresh = datetime.fromisoformat(rates["last_refresh"])
        if now - last_refresh < timedelta(minutes=5):
            need_update = False

    if need_update:
        now_str = now.isoformat()
        rates = {
            "EUR_USD": {"rate": round(random.uniform(1.05, 1.15), 4), "updated_at": now_str},
            "BTC_USD": {"rate": round(random.uniform(58000, 62000), 2), "updated_at": now_str},
            "ETH_USD": {"rate": round(random.uniform(2800, 3200), 2), "updated_at": now_str},
            "RUB_USD": {"rate": round(random.uniform(0.010, 0.012), 5), "updated_at": now_str},
            "source": "ParserServiceMock",
            "last_refresh": now_str
        }
        save_json(RATES_FILE, rates)

    return rates

def get_exchange_rate(from_currency: str, to_currency: str) -> tuple[float, str]:
    """Возвращает курс обмена и время его обновления."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0, datetime.now().isoformat()

    rates = get_all_rates()
     
    pair = f"{from_currency}_{to_currency}"
    if pair in rates:
        return rates[pair]["rate"], rates[pair]["updated_at"]
        
    reverse_pair = f"{to_currency}_{from_currency}"
    if reverse_pair in rates:
        return 1.0 / rates[reverse_pair]["rate"], rates[reverse_pair]["updated_at"]

    raise ValueError(f"Курс {from_currency}→{to_currency} недоступен.")

# ==========================================
# Внутренние функции работы с портфелем
# ==========================================

def _get_user_portfolio_model() -> Portfolio:
    """Загружает портфель текущего пользователя и возвращает объект Portfolio."""
    require_login()
    user_id = current_session["user_id"]
    portfolios_data = load_json(PORTFOLIOS_FILE, [])
    
    for p_data in portfolios_data:
        if p_data["user_id"] == user_id:
            return Portfolio(user_id=user_id, wallets_data=p_data.get("wallets", {}))
            
    return Portfolio(user_id=user_id)

def _save_user_portfolio_model(portfolio: Portfolio):
    """Сохраняет объект Portfolio обратно в JSON."""
    portfolios_data = load_json(PORTFOLIOS_FILE, [])
    
    wallets_dict = {}
    for code, wallet in portfolio.wallets.items():
        wallets_dict[code] = {
            "currency_code": code,
            "balance": wallet.balance
        }
        
    updated = False
    for i, p_data in enumerate(portfolios_data):
        if p_data["user_id"] == portfolio.user_id:
            portfolios_data[i]["wallets"] = wallets_dict
            updated = True
            break
            
    if not updated:
        portfolios_data.append({
            "user_id": portfolio.user_id,
            "wallets": wallets_dict
        })
        
    save_json(PORTFOLIOS_FILE, portfolios_data)

def get_portfolio_info(base_currency: str = "USD") -> dict:
    """Подготавливает данные о портфеле для команды show-portfolio."""
    portfolio = _get_user_portfolio_model()
    rates = get_all_rates()
    
    # Делегируем подсчет тотала модели
    total_value = portfolio.get_total_value(rates, base_currency)
    
    wallets_info = []
    for code, wallet in portfolio.wallets.items():
        rate, _ = get_exchange_rate(code, base_currency)
        value_in_base = wallet.balance * rate
        wallets_info.append({
            "currency": code,
            "balance": wallet.balance,
            "value_in_base": value_in_base
        })
        
    return {
        "base_currency": base_currency.upper(),
        "total_value": total_value,
        "wallets": wallets_info
    }
    
def buy_currency(currency_code: str, amount: float) -> dict:
    """Покупает указанную валюту за USD."""
    currency_code = currency_code.upper()
    if currency_code == "USD":
        raise ValueError("Нельзя купить USD за USD.")
        
    portfolio = _get_user_portfolio_model()
    
    rate, _ = get_exchange_rate(currency_code, "USD")
    cost_in_usd = amount * rate
    
    try:
        usd_wallet = portfolio.get_wallet("USD")
    except KeyError:
        raise ValueError("У вас нет USD-кошелька или на нем 0. Сначала пополните баланс.")
        
    usd_wallet.withdraw(cost_in_usd) 
    
    try:
        target_wallet = portfolio.get_wallet(currency_code)
    except KeyError:
        portfolio.add_currency(currency_code)
        target_wallet = portfolio.get_wallet(currency_code)
        
    target_wallet.deposit(amount)
    
    _save_user_portfolio_model(portfolio)
    
    return {
        "currency": currency_code,
        "amount": amount,
        "rate": rate,
        "cost": cost_in_usd,
        "new_balance": target_wallet.balance
    }

def sell_currency(currency_code: str, amount: float) -> dict:
    """Продает указанную валюту, зачисляя выручку в USD."""
    currency_code = currency_code.upper()
    if currency_code == "USD":
        raise ValueError("Нельзя продать USD за USD.")
        
    portfolio = _get_user_portfolio_model()
    
    wallet = portfolio.get_wallet(currency_code)
    wallet.withdraw(amount) 
    
    rate, _ = get_exchange_rate(currency_code, "USD")
    revenue_in_usd = amount * rate
    
    try:
        usd_wallet = portfolio.get_wallet("USD")
    except KeyError:
        portfolio.add_currency("USD")
        usd_wallet = portfolio.get_wallet("USD")
        
    usd_wallet.deposit(revenue_in_usd)
    
    _save_user_portfolio_model(portfolio)
    
    return {
        "currency": currency_code,
        "amount": amount,
        "rate": rate,
        "revenue": revenue_in_usd,
        "new_balance": wallet.balance
    }

def add_fiat_usd(amount: float) -> float:
    """Тестовая функция для зачисления USD-баланса, чтобы было на что торговать."""
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