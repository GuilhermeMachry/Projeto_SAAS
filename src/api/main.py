"""Ponto de entrada do Serviço 01: API REST Gateway (FastAPI)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import tenants, monitors

app = FastAPI(
    title="HardTrack Solutions — API Multi-Tenant",
    description=(
        "Serviço REST Gateway da plataforma SaaS de monitoramento de hardware. "
        "Gerencia o ciclo de vida dos tenants, cadastros de componentes monitorados e histórico "
        "com isolamento físico em silos TinyDB e conformidade com a LGPD."
    ),
    version="1.0.0",
)

# Habilitar CORS para permitir conexão com frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de Rotas
app.include_router(tenants.router)
app.include_router(monitors.router)


@app.get("/health", tags=["Infraestrutura"], summary="Healthcheck do serviço da API")
def healthcheck():
    """Endpoint de sondagem para monitoramento de saúde do container/serviço."""
    return {
        "status": "healthy",
        "service": "hardtrack-api",
        "version": "1.0.0",
        "tenancy_model": "silo-json-tinydb",
    }


@app.get("/", tags=["Infraestrutura"], summary="Status raiz")
def root():
    return {
        "message": "HardTrack Solutions SaaS API está operacional.",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
