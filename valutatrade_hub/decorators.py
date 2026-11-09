from functools import wraps

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.logging_config import setup_logging

logger = setup_logging()


def log_action(action_name: str, verbose: bool = False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from valutatrade_hub.core.usecases import current_session

            user_id = current_session.get("user_id", "UNKNOWN")

            try:
                result = func(*args, **kwargs)
                if isinstance(result, dict):
                    currency = result.get("currency", "")
                    amount = result.get("amount", "")
                    rate = result.get("rate", "")
                    msg = f"{action_name} user_id={user_id} currency='{currency}' amount={amount} rate={rate} base='USD' result=OK"
                else:
                    msg = f"{action_name} user_id={user_id} result=OK"

                logger.info(msg)
                return result
            except Exception as e:
                logger.error(
                    f"{action_name} user_id={user_id} result=ERROR error_type={type(e).__name__} error_message='{str(e)}'"
                )
                raise

        return wrapper

    return decorator

def handle_errors(func):
    """Декоратор для перехвата исключений бизнес-логики и красивого вывода в консоль."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InsufficientFundsError as e:
            print(f"{e}")
        except CurrencyNotFoundError as e:
            print(f"{e}")
            print(
                "Подсказка: используйте поддерживаемые коды (USD, EUR, RUB, BTC, ETH) или введите 'help'."
            )
        except ApiRequestError as e:
            print(f"{e}")
            print("Попробуйте повторить запрос позже или проверьте соединение с сетью.")
        except (ValueError, KeyError, PermissionError, TypeError) as e:
            print(f"Ошибка: {e}")
        except Exception as e:
            print(f"Неизвестная системная ошибка: {e}")

    return wrapper


def confirm_action(func):
    """Декоратор для подтверждения критических действий (покупка/продажа)."""

    def wrapper(*args, **kwargs):
        ans = (
            input("Вы уверены, что хотите выполнить эту операцию? (y/n): ")
            .strip()
            .lower()
        )
        if ans in ("y", "yes", "да"):
            return func(*args, **kwargs)
        else:
            print("Операция отменена.")

    return wrapper