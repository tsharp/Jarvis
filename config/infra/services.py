"""
config.infra.services
=====================
Service-Endpunkte — wohin TRION sich verbindet.

OLLAMA_BASE  : Primärer Ollama-Endpunkt (LLM-Inference). Nutzt service_endpoint_resolver
               für automatische Docker-interne Adresse, falls kein Env-Override gesetzt.
MCP_BASE     : Endpunkt des SQL-Memory MCP-Servers.
VALIDATOR_URL: Endpunkt des Validator-Service (nur aktiv wenn ENABLE_VALIDATION=true).
DB_PATH      : Pfad zur SQLite-Memory-Datenbank.
               Legacy: einige Tests patchen config.DB_PATH direkt — daher hier belassen.
"""
import os

from utils.service_endpoint_resolver import default_service_endpoint

OLLAMA_BASE = os.getenv("OLLAMA_BASE", default_service_endpoint("ollama", 11434))
MCP_BASE = os.getenv("MCP_BASE", "http://mcp-sql-memory:8081")
VALIDATOR_URL = os.getenv("VALIDATOR_URL", "http://validator-service:8000")
DB_PATH = os.getenv("DB_PATH", os.getenv("MEMORY_DB_PATH", "/app/data/memory.db"))
