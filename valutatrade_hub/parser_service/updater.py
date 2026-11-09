from datetime import datetime, timezone
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.utils import load_json
from .config import ParserConfig
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .storage import StorageManager

logger = setup_logging()

class RatesUpdater:
    def __init__(self):
        self.config = ParserConfig()
        self.storage = StorageManager(self.config)
        self.clients = {
            "coingecko": CoinGeckoClient(self.config),
            "exchangerate": ExchangeRateApiClient(self.config)
        }

    def run_update(self, source: str = None) -> int:
        logger.info("Starting rates update...")
        raw_rates = {}
        history_records = []
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        sources_to_run = [source] if source and source in self.clients else self.clients.keys()
        
        updated_count = 0
        errors = False
        
        for src in sources_to_run:
            client = self.clients[src]
            try:
                rates = client.fetch_rates()
                count = len(rates)
                logger.info(f"Fetching from {src.capitalize()}... OK ({count} rates)")
                
                for pair, rate_val in rates.items():
                    raw_rates[pair] = {
                        "rate": rate_val,
                        "updated_at": now_iso,
                        "source": src
                    }
                    from_c, to_c = pair.split("_")
                    history_records.append({
                        "id": f"{pair}_{now_iso}",
                        "from_currency": from_c,
                        "to_currency": to_c,
                        "rate": rate_val,
                        "timestamp": now_iso,
                        "source": src
                    })
                    updated_count += 1
            except ApiRequestError as e:
                errors = True
                logger.error(f"Failed to fetch from {src.capitalize()}: {e}")

        if updated_count > 0:
            existing_data = load_json(self.config.RATES_FILE_PATH, {"pairs": {}, "last_refresh": ""})
            existing_pairs = existing_data.get("pairs", {})
            existing_pairs.update(raw_rates)
            
            final_data = {
                "pairs": existing_pairs,
                "last_refresh": now_iso
            }
            logger.info(f"Writing {updated_count} new rates to {self.config.RATES_FILE_PATH.name}...")
            self.storage.save_rates(final_data)
            self.storage.append_history(history_records)
        
        if errors:
            raise ApiRequestError("Update completed with errors. Check logs for details.")
            
        return updated_count, now_iso