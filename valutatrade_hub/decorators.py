from functools import wraps
from datetime import datetime
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.core.usecases import current_session

logger = setup_logging()

def log_action(action_name: str, verbose: bool = False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            timestamp = datetime.now().isoformat()
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
                logger.error(f"{action_name} user_id={user_id} result=ERROR error_type={type(e).__name__} error_message='{str(e)}'")
                raise
        return wrapper
    return decorator