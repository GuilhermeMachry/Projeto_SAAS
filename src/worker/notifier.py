"""Despachante de notificações push via Telegram Bot API com suporte a links de afiliados."""

import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests

from src.core.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_MOCK_MODE,
    AFFILIATE_TAG,
)

logger = logging.getLogger("hardtrack.notifier")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class TelegramNotifier:
    """Implementa o envio de notificações push via Telegram Bot API."""

    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, mock_mode: bool = TELEGRAM_MOCK_MODE):
        self.bot_token = bot_token
        self.mock_mode = mock_mode or not bool(bot_token)

    def generate_affiliate_link(self, original_url: str) -> str:
        """Injeta a tag de afiliado da plataforma para viabilizar a monetização."""
        if not original_url.startswith("http"):
            return original_url
        
        parsed = urlparse(original_url)
        query_dict = parse_qs(parsed.query)
        query_dict["tag"] = [AFFILIATE_TAG]
        query_dict["utm_source"] = ["hardtrack_saas"]
        new_query = urlencode(query_dict, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    def send_price_alert(
        self,
        tenant_id: str,
        chat_id: str,
        component_name: str,
        current_price: float,
        target_price: float,
        original_url: str,
    ) -> bool:
        """Monta a mensagem de oportunidade e despacha para o Telegram do cliente."""
        affiliate_url = self.generate_affiliate_link(original_url)
        economia = max(0.0, target_price - current_price)

        message = (
            f"🔥 *OPORTUNIDADE DE PREÇO — HardTrack Solutions*\n\n"
            f"📦 *Componente:* `{component_name}`\n"
            f"💰 *Preço Atual:* `R$ {current_price:,.2f}`\n"
            f"🎯 *Sua Meta:* `R$ {target_price:,.2f}`\n"
            f"📉 *Economia Imediata:* `R$ {economia:,.2f}`\n\n"
            f"🛒 *Comprar Agora com Desconto:* [Clique Aqui na Loja]({affiliate_url})\n\n"
            f"_(Tenant: {tenant_id} | Alerta em Tempo Real)_"
        )

        if self.mock_mode:
            logger.info(
                f"[TelegramNotifier] [MOCK DISPATCH] Notificação push simulada com sucesso!\n"
                f"   Destinatário Chat ID: {chat_id} (Tenant: {tenant_id})\n"
                f"   Componente: {component_name} | Preço: R$ {current_price:.2f} <= Meta: R$ {target_price:.2f}\n"
                f"   Link de Afiliado: {affiliate_url}"
            )
            return True

        # Despacho real via API do Telegram
        api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

        try:
            resp = requests.post(api_url, json=payload, timeout=5.0)
            if resp.status_code == 200:
                logger.info(f"[TelegramNotifier] Alerta entregue com sucesso no Telegram do Chat ID {chat_id}.")
                return True
            else:
                logger.error(f"[TelegramNotifier] Erro ao enviar mensagem para Telegram ({resp.status_code}): {resp.text}")
                return False
        except Exception as exc:
            logger.error(f"[TelegramNotifier] Exceção na chamada da API do Telegram: {exc}")
            return False
