"""Serviço 02: Worker Autônomo de Monitoramento e Scraping."""

import time
import argparse
import logging
from typing import Dict, Any

from src.core.config import WORKER_POLL_INTERVAL_SECONDS
from src.core.storage import TenantStorageManager
from src.core.models import PriceRecord, AlertLog
from src.worker.scraper import ScraperEngine
from src.worker.notifier import TelegramNotifier

logger = logging.getLogger("hardtrack.worker")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class WorkerRunner:
    """Orquestrador do ciclo autônomo de varredura periódica dos silos dos tenants."""

    def __init__(
        self,
        storage: TenantStorageManager = None,
        scraper: ScraperEngine = None,
        notifier: TelegramNotifier = None,
    ):
        self.storage = storage or TenantStorageManager()
        self.scraper = scraper or ScraperEngine()
        self.notifier = notifier or TelegramNotifier()

    def run_cycle(self) -> Dict[str, Any]:
        """Executa um ciclo completo de varredura sobre todos os silos de tenants ativos."""
        start_time = time.time()
        tenant_ids = self.storage.list_tenant_ids()
        
        stats = {
            "tenants_processados": len(tenant_ids),
            "componentes_checados": 0,
            "cotacoes_sucesso": 0,
            "alertas_disparados": 0,
            "falhas": 0,
            "duracao_segundos": 0.0,
        }

        logger.info(f"[Worker] Iniciando ciclo de varredura. Tenants encontrados: {len(tenant_ids)}")

        for tenant_id in tenant_ids:
            try:
                tenant_profile = self.storage.get_tenant(tenant_id)
                if not tenant_profile:
                    continue
                
                targets = self.storage.list_targets(tenant_id)
                logger.info(f"[Worker] Processando Tenant '{tenant_id}' ({len(targets)} componentes)")

                for target in targets:
                    stats["componentes_checados"] += 1
                    try:
                        price = self.scraper.scrape_url(target.url)
                        if price is not None:
                            stats["cotacoes_sucesso"] += 1
                            alerta_disparado = price <= target.preco_alvo

                            # 1. Gravar cotação no histórico cronológico do silo do tenant
                            price_record = PriceRecord(
                                target_id=target.id,
                                nome_componente=target.nome_componente,
                                url=target.url,
                                preco_coletado=price,
                                preco_alvo=target.preco_alvo,
                                alerta_disparado=alerta_disparado,
                            )
                            self.storage.record_price(tenant_id, price_record)
                            self.storage.update_target_last_price(tenant_id, target.id, price)

                            # 2. Avaliação de Preço e Despacho de Notificação Push
                            if alerta_disparado:
                                stats["alertas_disparados"] += 1
                                logger.info(
                                    f"[Worker] 🎯 META ATINGIDA para {tenant_id}! "
                                    f"{target.nome_componente}: R$ {price:.2f} <= R$ {target.preco_alvo:.2f}"
                                )
                                self.notifier.send_price_alert(
                                    tenant_id=tenant_id,
                                    chat_id=tenant_profile.telegram_chat_id,
                                    component_name=target.nome_componente,
                                    current_price=price,
                                    target_price=target.preco_alvo,
                                    original_url=target.url,
                                )

                                # Gravar auditoria do alerta no silo
                                alert_log = AlertLog(
                                    tenant_id=tenant_id,
                                    target_id=target.id,
                                    mensagem=(
                                        f"Oportunidade detectada: R$ {price:.2f} "
                                        f"(Meta: R$ {target.preco_alvo:.2f})"
                                    ),
                                )
                                self.storage.record_alert(tenant_id, alert_log)
                        else:
                            stats["falhas"] += 1
                            logger.warning(
                                f"[Worker] Não foi possível obter preço para '{target.nome_componente}' "
                                f"do tenant '{tenant_id}'."
                            )

                    except Exception as exc:
                        stats["falhas"] += 1
                        logger.error(f"[Worker] Falha ao processar componente {target.id} do tenant {tenant_id}: {exc}")

            except Exception as exc:
                stats["falhas"] += 1
                logger.error(f"[Worker] Erro ao iterar tenant {tenant_id}: {exc}")

        stats["duracao_segundos"] = round(time.time() - start_time, 2)
        logger.info(
            f"[Worker] Ciclo concluído em {stats['duracao_segundos']}s: "
            f"{stats['cotacoes_sucesso']}/{stats['componentes_checados']} cotações com sucesso, "
            f"{stats['alertas_disparados']} alertas disparados, {stats['falhas']} falhas."
        )
        return stats

    def run_loop(self, interval_seconds: int = WORKER_POLL_INTERVAL_SECONDS):
        """Executa o Worker continuamente em background respeitando o intervalo configurado."""
        logger.info(f"[Worker] Loop autônomo iniciado (Intervalo de ciclo: {interval_seconds}s)")
        try:
            while True:
                self.run_cycle()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("[Worker] Loop interrompido manualmente pelo operador.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Worker de Monitoramento e Scraping - HardTrack SaaS")
    parser.add_argument("--once", action="store_true", help="Executa um único ciclo de varredura e encerra")
    parser.add_argument("--interval", type=int, default=WORKER_POLL_INTERVAL_SECONDS, help="Intervalo em segundos entre ciclos")
    args = parser.parse_args()

    runner = WorkerRunner()
    if args.once:
        runner.run_cycle()
    else:
        runner.run_loop(interval_seconds=args.interval)
