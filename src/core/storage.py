"""Gerenciador central de persistência e isolamento físico de Tenancy (Silo por Arquivo JSON)."""

import fcntl
import os
import re
import stat
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional
from tinydb import Query, TinyDB

from src.core.config import B2B_MAX_TARGETS, B2C_MAX_TARGETS, STORAGE_DIR
from src.core.models import (
    AlertLog,
    MonitorTargetCreate,
    MonitorTargetResponse,
    MonitorTargetUpdate,
    PriceRecord,
    SiloInfoResponse,
    TenantCreate,
    TenantResponse,
    TenantType,
)


class QuotaExceededError(Exception):
    """Exceção lançada quando o tenant atinge o limite de URLs do seu plano."""


class TenantStorageManager:
    """Implementa o isolamento estrito de dados através de arquivos independentes (Silos TinyDB).

    Cada tenant possui seu próprio arquivo: storage/tenants/tenant_<tenant_id>.json.
    Operações de leitura, escrita e exclusão (LGPD Art. 18) são rigidamente confinadas
    ao silo do respectivo cliente e protegidas por trava por tenant (RLock + fcntl.flock).
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._locks_dir = self.storage_dir / ".locks"
        self._locks_dir.mkdir(parents=True, exist_ok=True)
        self._thread_locks_guard = threading.Lock()
        self._thread_locks: Dict[str, threading.RLock] = {}

    def _get_thread_lock(self, clean_id: str) -> threading.RLock:
        with self._thread_locks_guard:
            lock = self._thread_locks.get(clean_id)
            if lock is None:
                lock = threading.RLock()
                self._thread_locks[clean_id] = lock
            return lock

    @contextmanager
    def _tenant_lock(self, tenant_id: str) -> Iterator[str]:
        """Adquire trava exclusiva (thread + arquivo POSIX) isolada para este tenant."""
        clean_id = self.sanitize_tenant_id(tenant_id)
        t_lock = self._get_thread_lock(clean_id)
        lock_file_path = self._locks_dir / f"tenant_{clean_id}.lock"
        with t_lock:
            self._locks_dir.mkdir(parents=True, exist_ok=True)
            with open(lock_file_path, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    yield clean_id
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def sanitize_tenant_id(self, tenant_id: str) -> str:
        """Sanitiza e valida o identificador do tenant contra ataques de Path Traversal.

        Aceita estritamente letras, dígitos, underline e hífen.
        Rejeita qualquer tentativa de navegação de diretório (ex: '../', '/').
        """
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValueError("O tenant_id é obrigatório e deve ser uma string não vazia.")

        clean_id = tenant_id.strip()
        if not re.match(r"^[a-zA-Z0-9_-]+$", clean_id):
            raise ValueError(
                f"Identificador de tenant inválido: '{tenant_id}'. "
                "Permitido apenas caracteres alfanuméricos, hífen e underline (Path Traversal bloqueado)."
            )
        return clean_id

    def get_silo_path(self, tenant_id: str) -> Path:
        """Retorna o caminho físico do arquivo silo exclusivo do tenant."""
        clean_id = self.sanitize_tenant_id(tenant_id)
        return self.storage_dir / f"tenant_{clean_id}.json"

    def _open_db(self, clean_id: str) -> TinyDB:
        """Abre uma conexão isolada com o arquivo de silo do tenant."""
        path = self.storage_dir / f"tenant_{clean_id}.json"
        return TinyDB(path, indent=2, ensure_ascii=False)

    @staticmethod
    def get_quota_for_type(tipo: TenantType) -> int:
        return B2B_MAX_TARGETS if tipo == TenantType.B2B_OFICINA else B2C_MAX_TARGETS

    # -------------------------------------------------------------
    # Ciclo de Vida do Tenant (Onboarding, Leitura e Expurgo LGPD)
    # -------------------------------------------------------------

    def create_or_update_tenant(self, data: TenantCreate) -> TenantResponse:
        """Cadastra ou atualiza um tenant em seu respectivo silo isolado."""
        now = datetime.now(timezone.utc).isoformat()
        with self._tenant_lock(data.tenant_id) as clean_id:
            with self._open_db(clean_id) as db:
                profile_table = db.table("profile")
                existing = profile_table.all()

                tenant_dict = {
                    "tenant_id": clean_id,
                    "nome": data.nome,
                    "tipo": data.tipo.value if isinstance(data.tipo, TenantType) else data.tipo,
                    "telegram_chat_id": data.telegram_chat_id,
                    "created_at": existing[0]["created_at"] if existing else now,
                    "updated_at": now,
                }

                profile_table.truncate()
                profile_table.insert(tenant_dict)

            # Ajusta permissões do arquivo no Linux (chmod 600 - leitura/escrita restrita)
            try:
                os.chmod(self.get_silo_path(clean_id), 0o600)
            except OSError:
                pass

        return TenantResponse(
            tenant_id=tenant_dict["tenant_id"],
            nome=tenant_dict["nome"],
            tipo=TenantType(tenant_dict["tipo"]),
            telegram_chat_id=tenant_dict["telegram_chat_id"],
            created_at=tenant_dict["created_at"],
        )

    def get_tenant(self, tenant_id: str) -> Optional[TenantResponse]:
        """Obtém os dados cadastrais do tenant caso o seu arquivo de silo exista."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return None

            with self._open_db(clean_id) as db:
                profile_table = db.table("profile")
                records = profile_table.all()
                if not records:
                    return None
                data = records[0]
                return TenantResponse(
                    tenant_id=data["tenant_id"],
                    nome=data["nome"],
                    tipo=TenantType(data["tipo"]),
                    telegram_chat_id=data["telegram_chat_id"],
                    created_at=data.get("created_at", ""),
                )

    def list_tenant_ids(self) -> List[str]:
        """Varre o diretório de armazenamento e lista todos os identificadores de tenants ativos."""
        tenants = []
        for file in self.storage_dir.glob("tenant_*.json"):
            match = re.match(r"^tenant_(.+)\.json$", file.name)
            if match:
                tenants.append(match.group(1))
        return sorted(tenants)

    def delete_tenant(self, tenant_id: str) -> bool:
        """Executa o Expurgo Atômico dos dados do tenant para cumprimento do Artigo 18 da LGPD.

        A deleção do arquivo físico no sistema de arquivos garante que nenhum dado pessoal,
        URL ou histórico permaneça armazenado na plataforma.
        """
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if path.exists():
                try:
                    path.unlink()
                    return True
                except OSError as exc:
                    raise RuntimeError(f"Erro ao excluir arquivo de silo do tenant: {exc}")
            return False

    def get_silo_info(self, tenant_id: str) -> Optional[SiloInfoResponse]:
        """Retorna metadados operacionais e de isolamento do arquivo silo do tenant."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return None

            st = path.stat()
            perms = oct(stat.S_IMODE(st.st_mode))
            with self._open_db(clean_id) as db:
                profile = db.table("profile").all()
                if not profile:
                    return None
                tipo = TenantType(profile[0]["tipo"])
                targets_count = len(db.table("targets").all())
                history_count = len(db.table("history").all())
                alerts_count = len(db.table("alerts").all())

            plan_name = "B2B Pro (Oficina / Montadora)" if tipo == TenantType.B2B_OFICINA else "B2C Freemium (Consumidor Final)"
            return SiloInfoResponse(
                tenant_id=clean_id,
                tipo=tipo,
                plan_name=plan_name,
                silo_filename=path.name,
                size_bytes=st.st_size,
                permissions_octal=perms,
                targets_count=targets_count,
                targets_quota=self.get_quota_for_type(tipo),
                history_count=history_count,
                alerts_count=alerts_count,
            )

    # -------------------------------------------------------------
    # Gestão de Componentes e Metas Monitoradas
    # -------------------------------------------------------------

    def add_target(
        self,
        tenant_id: str,
        data: MonitorTargetCreate,
        enforce_quota: bool = True,
    ) -> MonitorTargetResponse:
        """Adiciona um componente de hardware para monitoramento no silo do tenant."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                raise FileNotFoundError(
                    f"Tenant '{clean_id}' não encontrado. Cadastre o tenant antes de adicionar metas."
                )

            target_id = str(uuid.uuid4())[:8]
            now = datetime.now(timezone.utc).isoformat()

            record = {
                "id": target_id,
                "tenant_id": clean_id,
                "nome_componente": data.nome_componente,
                "url": str(data.url),
                "preco_alvo": float(data.preco_alvo),
                "ultimo_preco": None,
                "ultima_checagem": None,
                "criado_em": now,
            }

            with self._open_db(clean_id) as db:
                if enforce_quota:
                    profiles = db.table("profile").all()
                    if profiles:
                        tipo = TenantType(profiles[0]["tipo"])
                        quota = self.get_quota_for_type(tipo)
                        current_count = len(db.table("targets").all())
                        if current_count >= quota:
                            raise QuotaExceededError(
                                f"Cota do plano atingida ({current_count}/{quota} URLs para {tipo.value})."
                            )
                targets_table = db.table("targets")
                targets_table.insert(record)

            return MonitorTargetResponse(**record)

    def list_targets(self, tenant_id: str) -> List[MonitorTargetResponse]:
        """Lista todas as URLs e componentes monitorados pertencentes estritamente a este tenant."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return []

            with self._open_db(clean_id) as db:
                targets_table = db.table("targets")
                records = targets_table.all()
                return [MonitorTargetResponse(**r) for r in records]

    def get_target(self, tenant_id: str, target_id: str) -> Optional[MonitorTargetResponse]:
        """Busca um componente monitorado específico no silo do tenant."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return None

            with self._open_db(clean_id) as db:
                targets_table = db.table("targets")
                TargetQuery = Query()
                records = targets_table.search(TargetQuery.id == target_id)
                if records:
                    return MonitorTargetResponse(**records[0])
                return None

    def update_target(
        self,
        tenant_id: str,
        target_id: str,
        data: MonitorTargetUpdate,
    ) -> Optional[MonitorTargetResponse]:
        """Atualiza campos de um componente monitorado no silo do tenant."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return None

            updates = {}
            if data.nome_componente is not None:
                updates["nome_componente"] = data.nome_componente
            if data.url is not None:
                updates["url"] = str(data.url)
            if data.preco_alvo is not None:
                updates["preco_alvo"] = float(data.preco_alvo)

            with self._open_db(clean_id) as db:
                targets_table = db.table("targets")
                TargetQuery = Query()
                existing = targets_table.search(TargetQuery.id == target_id)
                if not existing:
                    return None
                if updates:
                    targets_table.update(updates, TargetQuery.id == target_id)
                updated_record = targets_table.search(TargetQuery.id == target_id)[0]
                return MonitorTargetResponse(**updated_record)

    def update_target_last_price(self, tenant_id: str, target_id: str, price: float) -> bool:
        """Atualiza a última cotação e timestamp de checagem do componente."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return False

            now = datetime.now(timezone.utc).isoformat()
            with self._open_db(clean_id) as db:
                targets_table = db.table("targets")
                TargetQuery = Query()
                updated = targets_table.update(
                    {"ultimo_preco": float(price), "ultima_checagem": now},
                    TargetQuery.id == target_id,
                )
                return len(updated) > 0

    def delete_target(self, tenant_id: str, target_id: str) -> bool:
        """Remove um componente de hardware da lista de monitoramento do tenant."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return False

            with self._open_db(clean_id) as db:
                targets_table = db.table("targets")
                TargetQuery = Query()
                removed = targets_table.remove(TargetQuery.id == target_id)
                return len(removed) > 0

    # -------------------------------------------------------------
    # Histórico de Preços e Auditoria de Alertas
    # -------------------------------------------------------------

    def record_price(self, tenant_id: str, record: PriceRecord):
        """Grava atômica e cronologicamente a leitura de preço no histórico do silo."""
        with self._tenant_lock(tenant_id) as clean_id:
            with self._open_db(clean_id) as db:
                history_table = db.table("history")
                history_table.insert(record.model_dump())

    def get_history(self, tenant_id: str, limit: int = 50) -> List[PriceRecord]:
        """Recupera o histórico cronológico de preços capturados para o tenant."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return []

            with self._open_db(clean_id) as db:
                history_table = db.table("history")
                records = history_table.all()
                sorted_records = sorted(records, key=lambda x: x.get("timestamp", ""), reverse=True)
                return [PriceRecord(**r) for r in sorted_records[:limit]]

    def record_alert(self, tenant_id: str, alert: AlertLog):
        """Grava log auditável de notificação disparada."""
        with self._tenant_lock(tenant_id) as clean_id:
            with self._open_db(clean_id) as db:
                alerts_table = db.table("alerts")
                alerts_table.insert(alert.model_dump())

    def list_alerts(self, tenant_id: str, limit: int = 50) -> List[AlertLog]:
        """Lista os alertas enviados ao tenant (mais recentes primeiro)."""
        with self._tenant_lock(tenant_id) as clean_id:
            path = self.storage_dir / f"tenant_{clean_id}.json"
            if not path.exists():
                return []

            with self._open_db(clean_id) as db:
                alerts_table = db.table("alerts")
                records = alerts_table.all()
                sorted_records = sorted(records, key=lambda x: x.get("timestamp", ""), reverse=True)
                return [AlertLog(**r) for r in sorted_records[:limit]]
