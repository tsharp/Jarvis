"""
config.infra.paths
==================
Dateisystem-Pfade & Logging-Level.

WORKSPACE_BASE: Root-Verzeichnis für Session-Workspaces (Chunking, Long-Context).
                Unterordner werden pro conversation_id angelegt.
LOG_LEVEL     : Python-Logging-Level (DEBUG / INFO / WARNING / ERROR).
"""
import os

WORKSPACE_BASE = os.getenv("WORKSPACE_BASE", "/tmp/trion/jarvis/workspace")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
