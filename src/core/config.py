"""Configurações globais e variáveis de ambiente do sistema."""

import os
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage" / "tenants"))

# Garantir existência do diretório de armazenamento
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Parâmetros de Scraping e Resiliência
SCRAPER_TIMEOUT_SECONDS = float(os.getenv("SCRAPER_TIMEOUT_SECONDS", "5.0"))
SCRAPER_MAX_RETRIES = int(os.getenv("SCRAPER_MAX_RETRIES", "3"))
DEFAULT_USER_AGENT = os.getenv(
    "DEFAULT_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 HardTrackBot/1.0"
)

# Parâmetros de Notificação e Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_MOCK_MODE = os.getenv("TELEGRAM_MOCK_MODE", "true").lower() in ("true", "1", "yes")

# Parâmetros de Negócio e Monetização
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "hardtrack-20")

# Intervalo padrão do loop do Worker (em segundos)
WORKER_POLL_INTERVAL_SECONDS = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "60"))
