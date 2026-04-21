"""
config.infra
============
Infrastruktur-Konfiguration — die unterste Schicht, kein Business-Wissen.

Module:
  adapter  → settings-Bootstrap (Fallback auf os.getenv)
  cors     → CORS-Whitelist & Toggle
  services → Service-Endpunkte (Ollama, MCP, Validator, DB)
  paths    → Dateisystem-Pfade & Log-Level

Re-Exports für bequemen Zugriff via `from config.infra import ...`:
"""
from config.infra.adapter import settings

from config.infra.cors import (
    ALLOW_ORIGINS,
    ALLOWED_ORIGINS,
    ENABLE_CORS,
)

from config.infra.services import (
    OLLAMA_BASE,
    MCP_BASE,
    VALIDATOR_URL,
    DB_PATH,
)

from config.infra.paths import (
    WORKSPACE_BASE,
    LOG_LEVEL,
)

__all__ = [
    "settings",
    "ALLOW_ORIGINS",
    "ALLOWED_ORIGINS",
    "ENABLE_CORS",
    "OLLAMA_BASE",
    "MCP_BASE",
    "VALIDATOR_URL",
    "DB_PATH",
    "WORKSPACE_BASE",
    "LOG_LEVEL",
]
