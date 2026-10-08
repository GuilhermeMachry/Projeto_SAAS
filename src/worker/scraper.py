"""Motor de Scraping resiliente com BeautifulSoup4, timeout estrito e retry exponencial."""

import re
import time
import logging
from typing import Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from src.core.config import (
    DEFAULT_USER_AGENT,
    SCRAPER_TIMEOUT_SECONDS,
    SCRAPER_MAX_RETRIES,
)

logger = logging.getLogger("hardtrack.scraper")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def parse_price_string(raw_text: str) -> Optional[float]:
    """Converte strings de preços (formatos BRL e USD) para float numérico.
    
    Exemplos aceitos:
    - 'R$ 1.899,99' -> 1899.99
    - 'R$ 850,00'   -> 850.00
    - '1899.99'     -> 1899.99
    - 'R$ 2.450'    -> 2450.00
    - 'R$ 2.450,00' -> 2450.00
    """
    if not raw_text:
        return None

    cleaned = raw_text.replace("\xa0", " ").strip()
    match = re.search(r"(?:R?\$?\s*)?([0-9]+(?:[\.,][0-9]+)*)", cleaned)
    if not match:
        return None

    num_str = match.group(1).strip()
    if "," in num_str and "." in num_str:
        num_str = num_str.replace(".", "").replace(",", ".")
    elif "," in num_str:
        num_str = num_str.replace(",", ".")
    elif "." in num_str:
        parts = num_str.split(".")
        if len(parts) == 2:
            if len(parts[1]) == 3 and len(parts[0]) <= 3:
                num_str = parts[0] + parts[1]
        else:
            num_str = "".join(parts)

    try:
        val = float(num_str)
        return val if val > 0 else None
    except ValueError:
        return None


class ScraperEngine:
    """Implementa coleta de preços com resiliência, retry exponencial e tolerância a falhas."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = SCRAPER_TIMEOUT_SECONDS,
        max_retries: int = SCRAPER_MAX_RETRIES,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries

    def scrape_url(self, url: str) -> Optional[float]:
        """Extrai o preço da URL com tratamento gracioso de erros (0% de crashes).
        
        Suporta URLs de teste (prefixo 'mock://' ou 'test://') para execuções determinísticas.
        """
        # Suporte a ambiente de testes / mocks determinísticos
        if url.startswith("mock://") or url.startswith("test://"):
            return self._handle_mock_url(url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                if response.status_code == 200:
                    price = self._extract_price_from_html(response.text)
                    if price is not None:
                        return price
                    logger.warning(f"[Scraper] Preço não encontrado na página (seletor DOM nulo): {url}")
                    return None
                elif 500 <= response.status_code < 600:
                    logger.warning(
                        f"[Scraper] Erro transitório {response.status_code} na URL {url}. "
                        f"Tentativa {attempt}/{self.max_retries}."
                    )
                else:
                    logger.warning(f"[Scraper] Resposta HTTP {response.status_code} para {url}. Abortando tentativas.")
                    return None

            except (requests.Timeout, requests.ConnectionError) as exc:
                logger.warning(
                    f"[Scraper] Falha de conexão/timeout ({type(exc).__name__}) na tentativa "
                    f"{attempt}/{self.max_retries} para {url}."
                )
            except Exception as exc:
                logger.error(f"[Scraper] Exceção inesperada ao raspar {url}: {exc}")
                return None

            # Exponential Backoff: espera proporcional antes de retentar
            if attempt < self.max_retries:
                backoff = 0.5 * (2 ** (attempt - 1))
                time.sleep(backoff)

        logger.error(f"[Scraper] Falha definitiva após {self.max_retries} tentativas: {url}")
        return None

    def _extract_price_from_html(self, html_content: str) -> Optional[float]:
        """Tenta extrair o preço utilizando seletores comuns de e-commerces brasileiros."""
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Busca por meta tags semânticas (schema.org)
        meta_price = soup.find("meta", property="product:price:amount") or soup.find("meta", itemprop="price")
        if meta_price and meta_price.get("content"):
            parsed = parse_price_string(meta_price["content"])
            if parsed:
                return parsed

        # 2. Busca por classes e IDs convencionais de e-commerce
        selectors = [
            ".price", ".preco", ".finalPrice", ".val-price",
            "[data-testid='price']", ".product-price", "#preco",
            ".sale-price", ".preco-promocional", ".pricing__value"
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                parsed = parse_price_string(elem.get_text())
                if parsed:
                    return parsed

        # 3. Varredura textual por padrões monetários explícitos 'R$'
        for text_node in soup.find_all(text=re.compile(r"R\$\s*\d+")):
            parsed = parse_price_string(str(text_node))
            if parsed and parsed > 10:  # Descarta valores espúrios menores que R$ 10
                return parsed

        return None

    def _handle_mock_url(self, url: str) -> Optional[float]:
        """Processa URLs simuladas para testes determinísticos sem chamada de rede."""
        # Formato: mock://hardware.store/product?price=1899.90
        match = re.search(r"price=([0-9]+(?:\.[0-9]+)?)", url)
        if match:
            return float(match.group(1))
        # Formato mock de falha intencional
        if "fail" in url or "timeout" in url:
            return None
        return 1999.00
