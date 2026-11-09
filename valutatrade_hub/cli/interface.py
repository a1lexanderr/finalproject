import shlex
from prettytable import PrettyTable
from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import InsufficientFundsError, CurrencyNotFoundError, ApiRequestError

def handle_errors(func):
    """Декоратор для перехвата исключений бизнес-логики и красивого вывода в консоль."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InsufficientFundsError as e:
            print(f"{e}")
        except CurrencyNotFoundError as e:
            print(f"{e}")
            print("Подсказка: используйте поддерживаемые коды (USD, EUR, RUB, BTC, ETH) или введите 'help'.")
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
        ans = input("Вы уверены, что хотите выполнить эту операцию? (y/n): ").strip().lower()
        if ans in ('y', 'yes', 'да'):
            return func(*args, **kwargs)
        else:
            print("Операция отменена.")
    return wrapper

def parse_args(tokens: list[str]) -> dict:
    """
    Простой парсер аргументов вида '--key value'.
    Пример: ['--currency', 'BTC', '--amount', '0.05'] -> {'currency': 'BTC', 'amount': '0.05'}
    """
    args = {}
    i = 0
    while i < len(tokens):
        if tokens[i].startswith("--"):
            key = tokens[i][2:]
            if i + 1 < len(tokens) and not tokens[i+1].startswith("--"):
                args[key] = tokens[i+1]
                i += 2
            else:
                args[key] = True
                i += 1
        else:
            i += 1
    return args

def require_args(parsed_args: dict, required: list[str]):
    """Проверяет, все ли обязательные аргументы переданы."""
    for req in required:
        if req not in parsed_args:
            raise ValueError(f"Пропущен обязательный аргумент: --{req}")


@handle_errors
def handle_register(parsed_args: dict):
    require_args(parsed_args, ["username", "password"])
    user = usecases.register_user(parsed_args["username"], parsed_args["password"])
    print(f"Пользователь '{user.username}' успешно зарегистрирован (id={user.user_id}).\nВойдите: login --username {user.username} --password ****")

@handle_errors
def handle_login(parsed_args: dict):
    require_args(parsed_args, ["username", "password"])
    user = usecases.login_user(parsed_args["username"], parsed_args["password"])
    print(f"Вы вошли как '{user.username}'.")

@handle_errors
def handle_show_portfolio(parsed_args: dict):
    base = parsed_args.get("base", "USD")
    data = usecases.get_portfolio_info(base_currency=base)
    
    print(f"\nПортфель (база: {data['base_currency']}):")
    if not data["wallets"]:
        print("Ваш портфель пуст.")
        return

    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", f"Оценка в {data['base_currency']}"]
    table.align = "r"
    table.align["Валюта"] = "l"
    
    for w in data["wallets"]:
        table.add_row([
            w["currency"], 
            f"{w['balance']:.4f}", 
            f"{w['value_in_base']:.2f}"
        ])
        
    print(table)
    print(f"ИТОГО: {data['total_value']:,.2f} {data['base_currency']}\n")

@handle_errors
@confirm_action
def handle_buy(parsed_args: dict):
    require_args(parsed_args, ["currency", "amount"])
    amount = float(parsed_args["amount"])
    result = usecases.buy_currency(parsed_args["currency"], amount)
    print(f"Покупка выполнена: {result['amount']:.4f} {result['currency']} по курсу {result['rate']:.4f} USD")
    print(f"Оценочная стоимость: {result['cost']:.2f} USD")
    print(f"Текущий баланс {result['currency']}: {result['new_balance']:.4f}")

@handle_errors
@confirm_action
def handle_sell(parsed_args: dict):
    require_args(parsed_args, ["currency", "amount"])
    amount = float(parsed_args["amount"])
    result = usecases.sell_currency(parsed_args["currency"], amount)
    print(f"Продажа выполнена: {result['amount']:.4f} {result['currency']} по курсу {result['rate']:.4f} USD")
    print(f"Выручка: {result['revenue']:.2f} USD")
    print(f"Текущий баланс {result['currency']}: {result['new_balance']:.4f}")

@handle_errors
def handle_get_rate(parsed_args: dict):
    require_args(parsed_args, ["from", "to"])
    rate, updated_at = usecases.get_exchange_rate(parsed_args["from"], parsed_args["to"])
    print(f"Курс {parsed_args['from'].upper()}→{parsed_args['to'].upper()}: {rate:.8f} (обновлено: {updated_at})")

@handle_errors
def handle_add_fiat(parsed_args: dict):
    """Скрытая команда для пополнения USD."""
    require_args(parsed_args, ["amount"])
    amount = float(parsed_args["amount"])
    new_balance = usecases.add_fiat_usd(amount)
    print(f"Баланс пополнен. Текущий баланс USD: {new_balance:.2f}")

@handle_errors
def handle_update_rates(parsed_args: dict):
    from valutatrade_hub.parser_service.updater import RatesUpdater
    source = parsed_args.get("source")
    updater = RatesUpdater()
    try:
        count, timestamp = updater.run_update(source)
        print(f"✅ Успешно обновлено {count} курсов. Последнее обновление: {timestamp}")
    except Exception as e:
        print(f"⚠️ {e}")
        
@handle_errors
def handle_show_rates(parsed_args: dict):
    from valutatrade_hub.core.utils import load_json
    from valutatrade_hub.parser_service.config import ParserConfig
    
    config = ParserConfig()
    data = load_json(config.RATES_FILE_PATH, {"pairs": {}, "last_refresh": None})
    pairs = data.get("pairs", {})
    
    if not pairs:
        print("❌ Локальный кеш курсов пуст. Выполните 'update-rates', чтобы загрузить данные.")
        return
        
    target_currency = parsed_args.get("currency", "").upper()
    top_n = int(parsed_args.get("top", 0))
    
    rates_list = []
    for pair, info in pairs.items():
        if target_currency and target_currency not in pair:
            continue
        rates_list.append({
            "pair": pair,
            "rate": info["rate"],
            "updated_at": info["updated_at"]
        })
        
    if target_currency and not rates_list:
        print(f"❌ Курс для '{target_currency}' не найден в кеше.")
        return
        
    if top_n > 0:
        rates_list.sort(key=lambda x: x["rate"], reverse=True)
        rates_list = rates_list[:top_n]
        
    print(f"\n📊 Rates from cache (updated at {data.get('last_refresh')}):")
    for r in rates_list:
        print(f"- {r['pair']}: {r['rate']:.8f}")

def run_cli():
    print("=" * 50)
    print("Добро пожаловать в ValutaTrade Hub!")
    print("Введите 'help' для списка команд или 'exit' для выхода.")
    print("=" * 50)
    
    commands = {
        "register": handle_register,
        "login": handle_login,
        "show-portfolio": handle_show_portfolio,
        "buy": handle_buy,
        "sell": handle_sell,
        "get-rate": handle_get_rate,
        "update-rates": handle_update_rates,
        "show-rates": handle_show_rates,
        "add-fiat": handle_add_fiat
    }

    while True:
        try:
            command_line = input("\n> ").strip()
            if not command_line:
                continue
                
            if command_line.lower() in ('exit', 'quit'):
                print("До свидания!")
                break
            
            if command_line.lower() == 'help':
                print("Доступные команды:")
                print("  register --username <str> --password <str>")
                print("  login --username <str> --password <str>")
                print("  show-portfolio [--base <str>]")
                print("  buy --currency <str> --amount <float>")
                print("  sell --currency <str> --amount <float>")
                print("  get-rate --from <str> --to <str>")
                print("  add-fiat --amount <float> (тестовая команда пополнения USD)")
                continue

            tokens = shlex.split(command_line)
            
            command = tokens[0].lower()
            if command in commands:
                parsed_args = parse_args(tokens[1:])
                commands[command](parsed_args)
            else:
                print(f"Неизвестная команда: '{command}'. Введите 'help'.")
                
        except KeyboardInterrupt:
            print("\nВыход...")
            break
        except Exception as e:
            print(f"Системная ошибка: {e}")