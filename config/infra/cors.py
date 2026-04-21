"""
config.infra.cors
=================
CORS-Konfiguration — wer darf auf die API zugreifen.

ALLOW_ORIGINS  : Explizite Whitelist für FastAPI CORSMiddleware.
ALLOWED_ORIGINS: Wildcard-String für Header (z.B. nginx, legacy-Middleware).
ENABLE_CORS    : Master-Toggle — auf false setzen, um CORS komplett zu deaktivieren.
"""
import os

ALLOW_ORIGINS = [
    "http://localhost:8400",
    "http://localhost:8100",
]

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
ENABLE_CORS = os.getenv("ENABLE_CORS", "true").lower() == "true"
