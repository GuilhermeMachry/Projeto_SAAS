"""Testes de resiliência, parsing de preços e ciclo autônomo do Worker."""

from src.core.storage import TenantStorageManager
from src.core.models import TenantCreate, TenantType, MonitorTargetCreate
from src.worker.scraper import parse_price_string, ScraperEngine
from src.worker.notifier import TelegramNotifier
from src.worker.runner import WorkerRunner


def test_parse_price_formats():
    """Valida o parser em múltiplos formatos de moeda encontrados em e-commerces."""
    assert parse_price_string("R$ 1.899,99") == 1899.99
    assert parse_price_string("R$ 850,00") == 850.00
    assert parse_price_string("1899.99") == 1899.99
    assert parse_price_string("R$ 2.450") == 2450.00
    assert parse_price_string("Por apenas R$ 499,90 à vista") == 499.90
    assert parse_price_string("Sem estoque") is None
    assert parse_price_string("") is None


def test_scraper_resilience_on_failure():
    """Verifica se o Scraper lida graciosamente com falhas sem causar crash (0% crashes)."""
    engine = ScraperEngine(timeout=1.0, max_retries=1)
    
    # URL inválida que lança exceção de conexão
    price = engine.scrape_url("http://dominio-totalmente-inexistente-12345.com/produto")
    assert price is None  # Degrada graciosamente sem estourar exceção não tratada

    # URL simulada de falha
    mock_fail = engine.scrape_url("mock://loja.com/fail")
    assert mock_fail is None


def test_worker_cycle_triggers_alert_and_records_history(storage: TenantStorageManager):
    """Executa um ciclo do Worker e valida que metas batidas geram alerta e histórico."""
    # Criar tenant com meta
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="worker_test", nome="Teste Worker", tipo=TenantType.B2C_ENTUSIASTA, telegram_chat_id="555")
    )
    storage.add_target(
        "worker_test",
        MonitorTargetCreate(
            nome_componente="Memória RAM 32GB DDR5",
            url="mock://loja.com/ram?price=650.00",
            preco_alvo=700.00,  # Preço atual (650) <= Preço alvo (700) -> DISPARA ALERTA!
        ),
    )

    scraper = ScraperEngine()
    notifier = TelegramNotifier(mock_mode=True)
    worker = WorkerRunner(storage=storage, scraper=scraper, notifier=notifier)

    stats = worker.run_cycle()
    assert stats["tenants_processados"] >= 1
    assert stats["componentes_checados"] >= 1
    assert stats["cotacoes_sucesso"] >= 1
    assert stats["alertas_disparados"] >= 1

    # Verificar gravação no silo do tenant
    history = storage.get_history("worker_test")
    assert len(history) == 1
    assert history[0].preco_coletado == 650.00
    assert history[0].alerta_disparado is True

    alerts = storage.list_alerts("worker_test")
    assert len(alerts) == 1
    assert "Oportunidade" in alerts[0].mensagem
