import uuid
import hashlib
from datetime import datetime
from .utils import load_json, save_json, USERS_FILE, PORTFOLIOS_FILE
from .models import User

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