"""Modelos de domínio e schemas Pydantic com a Linguagem Ubíqua do sistema."""

from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field, HttpUrl


class TenantType(str, Enum):
    B2C_ENTUSIASTA = "B2C_ENTUSIASTA"
    B2B_OFICINA = "B2B_OFICINA"


class TenantCreate(BaseModel):
    tenant_id: str = Field(..., min_length=3, max_length=50, description="Identificador único do tenant")
    nome: str = Field(..., min_length=2, max_length=100, description="Nome do usuário ou razão social")
    tipo: TenantType = Field(default=TenantType.B2C_ENTUSIASTA, description="Perfil do tenant")
    telegram_chat_id: str = Field(..., min_length=3, max_length=30, description="Telegram Chat ID numérico")


class TenantResponse(BaseModel):
    tenant_id: str
    nome: str
    tipo: TenantType
    telegram_chat_id: str
    created_at: str


class MonitorTargetCreate(BaseModel):
    nome_componente: str = Field(..., min_length=2, max_length=150, description="Nome da peça de hardware")
    url: str = Field(..., description="URL da página do e-commerce")
    preco_alvo: float = Field(..., gt=0, description="Preço teto desejado pelo tenant em R$")


class MonitorTargetResponse(BaseModel):
    id: str
    tenant_id: str
    nome_componente: str
    url: str
    preco_alvo: float
    ultimo_preco: Optional[float] = None
    ultima_checagem: Optional[str] = None
    criado_em: str


class PriceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_id: str
    nome_componente: str
    url: str
    preco_coletado: float
    preco_alvo: float
    alerta_disparado: bool
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AlertLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    target_id: str
    mensagem: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    canal: str = "Telegram"
    status: str = "ENVIADO"
