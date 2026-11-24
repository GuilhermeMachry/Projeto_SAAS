"""Configurações globais e variáveis de ambiente do sistema."""

import os
from pathlib import Path
from typing import List

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage" / "tenants"))

# Garantir existência do diretório de armazenamento
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Ambiente de execução ("development", "test", "production")
HARDTRACK_ENV = os.getenv("HARDTRACK_ENV", "development").lower()

# Segurança, Autenticação e Autorização (Secrets via ambiente)
# Em produção, defina HARDTRACK_SECRET_KEY e HARDTRACK_ADMIN_KEY obrigatoriamente via ambiente.
HARDTRACK_SECRET_KEY = os.getenv(
    "HARDTRACK_SECRET_KEY",
    "dev-only-hardtrack-hmac-secret-change-in-production",
)
HARDTRACK_ADMIN_KEY = os.getenv(
    "HARDTRACK_ADMIN_KEY",
    "dev-only-hardtrack-admin-key",
)
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "86400"))  # 24h

# CORS — Restringe origens permitidas (evita wildcard '*' com allow_credentials=True)
_raw_cors = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_cors.split(",") if o.strip()]

# Rate Limiting por Tenant (proteção contra Noisy Neighbor -> HTTP 429)
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "1200"))

# Cotas por plano de Tenant (alinhado com docs/visao.md)
B2C_MAX_TARGETS = int(os.getenv("B2C_MAX_TARGETS", "5"))
B2B_MAX_TARGETS = int(os.getenv("B2B_MAX_TARGETS", "50"))

# Permissão de URLs simuladas (mock:// / test://) para testes determinísticos e demo local
ALLOW_MOCK_URLS = os.getenv("ALLOW_MOCK_URLS", "true").lower() in ("true", "1", "yes")

# Parâmetros de Scraping e Resiliência
SCRAPER_TIMEOUT_SECONDS = float(os.getenv("SCRAPER_TIMEOUT_SECONDS", "5.0"))
SCRAPER_MAX_RETRIES = int(os.getenv("SCRAPER_MAX_RETRIES", "3"))
DEFAULT_USER_AGENT = os.getenv(
    "DEFAULT_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 HardTrackBot/1.0",
)

# Parâmetros de Notificação e Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_MOCK_MODE = os.getenv("TELEGRAM_MOCK_MODE", "true").lower() in ("true", "1", "yes")

# Parâmetros de Negócio e Monetização
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "hardtrack-20")

# Intervalo padrão do loop do Worker (em segundos)
WORKER_POLL_INTERVAL_SECONDS = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "60"))
