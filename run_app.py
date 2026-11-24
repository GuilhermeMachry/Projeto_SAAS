#!/usr/bin/env python3
"""Inicializador nativo da Interface Interativa + API do HardTrack Solutions.

Uso:
    .venv/bin/python run_app.py
    .venv/bin/python run_app.py --port 8000 --no-browser
"""

import argparse
import threading
import time
import webbrowser

import uvicorn

from src.core.models import MonitorTargetCreate, TenantCreate, TenantType
from src.core.storage import TenantStorageManager
from src.worker.notifier import TelegramNotifier
from src.worker.runner import WorkerRunner
from src.worker.scraper import ScraperEngine


def seed_demo_tenants_if_needed() -> None:
    """Garante que os dois perfis demo (B2C Gamer e B2B Oficina) estejam prontos para visualização."""
    storage = TenantStorageManager()
    seeded_any = False

    if storage.get_tenant("joao_b2c") is None:
        storage.create_or_update_tenant(
            TenantCreate(
                tenant_id="joao_b2c",
                nome="João Silva (Gamer / B2C)",
                tipo=TenantType.B2C_ENTUSIASTA,
                telegram_chat_id="11223344",
            )
        )
        storage.add_target(
            "joao_b2c",
            MonitorTargetCreate(
                nome_componente="GeForce RTX 4060 Ti 8GB",
                url="mock://kabum.com.br/rtx4060ti?price=2350.00",
                preco_alvo=2400.00,
            ),
        )
        seeded_any = True

    if storage.get_tenant("techparts_b2b") is None:
        storage.create_or_update_tenant(
            TenantCreate(
                tenant_id="techparts_b2b",
                nome="Oficina TechParts (Montadora / B2B)",
                tipo=TenantType.B2B_OFICINA,
                telegram_chat_id="99887766",
            )
        )
        storage.add_target(
            "techparts_b2b",
            MonitorTargetCreate(
                nome_componente="Processador AMD Ryzen 7 7800X3D",
                url="mock://terabyte.com.br/ryzen7800x3d?price=2799.00",
                preco_alvo=2900.00,
            ),
        )
        storage.add_target(
            "techparts_b2b",
            MonitorTargetCreate(
                nome_componente="SSD NVMe Kingston Fury 2TB PCIe 4.0",
                url="mock://pichau.com.br/ssd2tb?price=1150.00",
                preco_alvo=950.00,
            ),
        )
        seeded_any = True

    if seeded_any:
        worker = WorkerRunner(
            storage=storage,
            scraper=ScraperEngine(),
            notifier=TelegramNotifier(mock_mode=True),
        )
        worker.run_cycle()


def open_browser_later(url: str) -> None:
    time.sleep(1.3)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="HardTrack Solutions — Interface Web Nativa")
    parser.add_argument("--host", default="127.0.0.1", help="Host de bind (padrão: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Porta HTTP (padrão: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Não abre o navegador automaticamente")
    args = parser.parse_args()

    seed_demo_tenants_if_needed()

    url = f"http://{args.host}:{args.port}/app"
    print("=" * 72)
    print("  HardTrack Solutions — SaaS Multi-Tenant (Interface Nativa)")
    print(f"  Interface Interativa: {url}")
    print(f"  Swagger / OpenAPI:    http://{args.host}:{args.port}/docs")
    print("  Perfis Prontos:       Tenant A (B2C Gamer) & Tenant B (B2B Oficina)")
    print("=" * 72)

    if not args.no_browser:
        threading.Thread(target=open_browser_later, args=(url,), daemon=True).start()

    uvicorn.run("src.api.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
