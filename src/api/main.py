"""Ponto de entrada do Serviço 01: API REST Gateway (FastAPI) + Interface Web Nativa."""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import monitors, tenants
from src.core.config import CORS_ALLOWED_ORIGINS

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="HardTrack Solutions — API Multi-Tenant",
    description=(
        "Serviço REST Gateway da plataforma SaaS de monitoramento de hardware. "
        "Gerencia o ciclo de vida dos tenants, autenticação/autorização HMAC-SHA256, "
        "cadastros de componentes monitorados e histórico com isolamento físico em silos TinyDB "
        "e conformidade com a LGPD."
    ),
    version="1.1.0",
)

# CORS restrito a origens confiáveis (corrige achado de segurança wildcard '*' + credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-Token", "X-Tenant-ID", "X-Admin-Key"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Injeta cabeçalhos de segurança HTTP padrão em todas as respostas."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# Registro de Rotas
app.include_router(tenants.auth_router)
app.include_router(tenants.router)
app.include_router(monitors.router)

# Servir assets estáticos da interface web nativa
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/health", tags=["Infraestrutura"], summary="Healthcheck do serviço da API")
def healthcheck():
    """Endpoint de sondagem para monitoramento de saúde do container/serviço."""
    return {
        "status": "healthy",
        "service": "hardtrack-api",
        "version": "1.1.0",
        "tenancy_model": "silo-json-tinydb",
        "authz": "hmac-sha256-bearer",
    }


@app.get("/api/status", tags=["Infraestrutura"], summary="Status JSON da API")
def api_status():
    return {
        "message": "HardTrack Solutions SaaS API está operacional.",
        "docs": "/docs",
        "health": "/health",
        "ui": "/app",
    }


@app.get("/", include_in_schema=False)
@app.get("/app", include_in_schema=False)
def serve_web_app(request: Request):
    """Serve a interface web interativa nativa quando acessada pelo navegador."""
    index_file = WEB_DIR / "index.html"
    accept = request.headers.get("accept", "")
    if index_file.exists() and ("text/html" in accept or request.url.path == "/app"):
        return FileResponse(index_file)
    return JSONResponse(
        {
            "message": "HardTrack Solutions SaaS API está operacional.",
            "docs": "/docs",
            "health": "/health",
            "ui": "/app",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
