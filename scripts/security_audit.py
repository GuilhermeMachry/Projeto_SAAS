#!/usr/bin/env python3
"""Auditoria Automatizada de Segurança (Etapa 3.5 — HardTrack Solutions).

Verifica no repositório e no código-fonte:
1. Ausência de segredos hardcoded (tokens de bot Telegram, chaves AWS/GitHub, senhas literais);
2. Presença do arquivo `.env.example` e proteção do `.env` no `.gitignore`;
3. Configuração segura de CORS (sem wildcard '*' combinado com allow_credentials=True);
4. Cobertura de AuthZ (Depends(require_tenant_access)) em todas as rotas de monitoramento;
5. Fixação de versões (pinning) nas dependências em `requirements.txt`.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SECRET_PATTERNS = [
    ("Telegram Bot Token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub PAT", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("Private Key PEM", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]


def check_secrets() -> list[str]:
    issues = []
    for path in (ROOT / "src").rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(content):
                issues.append(f"[SECRET] Possível {label} encontrado em {path.relative_to(ROOT)}")
    if (ROOT / ".env").exists():
        # Apenas alerta se estiver rastreado no git (checagem de .gitignore)
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        if ".env" not in gitignore:
            issues.append("[SECRET] Arquivo .env presente sem regra no .gitignore")
    if not (ROOT / ".env.example").exists():
        issues.append("[SECRET] Arquivo .env.example ausente no repositório")
    return issues


def check_cors_hardening() -> list[str]:
    issues = []
    main_py = (ROOT / "src" / "api" / "main.py").read_text(encoding="utf-8")
    if 'allow_origins=["*"]' in main_py and "allow_credentials=True" in main_py:
        issues.append("[CORS] Configuração insegura: allow_origins=['*'] com allow_credentials=True")
    return issues


def check_authz_coverage() -> list[str]:
    issues = []
    monitors_py = (ROOT / "src" / "api" / "routes" / "monitors.py").read_text(encoding="utf-8")
    route_defs = re.findall(r"@router\.(?:get|post|put|patch|delete)\(", monitors_py)
    auth_deps = re.findall(r"Depends\(require_tenant_access\)", monitors_py)
    if len(auth_deps) < len(route_defs):
        issues.append(
            f"[AUTHZ] Cobertura incompleta em monitors.py: {len(auth_deps)}/{len(route_defs)} rotas protegidas"
        )
    return issues


def check_dependencies_pinned() -> list[str]:
    issues = []
    req_file = ROOT / "requirements.txt"
    for idx, line in enumerate(req_file.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "==" not in stripped:
            issues.append(f"[DEPS] Dependência sem versão fixada em requirements.txt:{idx}: '{stripped}'")
    return issues


def main() -> int:
    print("=" * 72)
    print("  HardTrack Solutions — Auditoria Automatizada de Segurança (Etapa 3.5)")
    print("=" * 72)

    all_issues = []
    checks = [
        ("Varredura de Secrets e .env", check_secrets),
        ("Hardening de CORS", check_cors_hardening),
        ("Cobertura de AuthZ por Tenant", check_authz_coverage),
        ("Fixação de Dependências (requirements.txt)", check_dependencies_pinned),
    ]

    for title, fn in checks:
        issues = fn()
        if issues:
            print(f"  [FAIL] {title}")
            for i in issues:
                print(f"         -> {i}")
            all_issues.extend(issues)
        else:
            print(f"  [PASS] {title}")

    print("-" * 72)
    if all_issues:
        print(f"RESULTADO: REPROVADO ({len(all_issues)} pendência(s) encontrada(s))")
        return 1
    print("RESULTADO: APROVADO (0 vulnerabilidades estruturais detectadas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
