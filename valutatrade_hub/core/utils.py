import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


def load_json(filepath: Path, default_data):
    """Читает данные из JSON. Если файла нет, возвращает default_data."""
    if not filepath.exists():
        return default_data
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default_data


def save_json(filepath: Path, data):
    """Сохраняет данные в JSON с красивым форматированием."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
