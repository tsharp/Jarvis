"""
MCP Registry - Zentrale Verwaltung aller MCPs
Definiert welche MCPs aktiv sind und wie sie erreicht werden.
Unterstützte Transports:
- sse:    Legacy SSE-only
- stdio:  Stdin/Stdout (lokale Prozesse)
"""

import os
from typing import Dict, Any


# ═══════════════════════════════════════════════════════════════
# MCP KONFIGURATION
# ═══════════════════════════════════════════════════════════════

MCPS: Dict[str, Dict[str, Any]] = {
    
    # ─────────────────────────────────────────────────────────────
    # CORE: SQL Memory
    # ─────────────────────────────────────────────────────────────
    "sql-memory": {
        "url": os.getenv("MCP_SQL_MEMORY", "http://mcp-sql-memory:8081/mcp"),
        "enabled": True,
        "description": "Persistentes Memory mit Facts, Embeddings und Knowledge Graph",
    },

    # ─────────────────────────────────────────────────────────────
    # CORE: Sequential Thinking v2.0 (mit CIM Integration)
    # ─────────────────────────────────────────────────────────────
    "sequential-thinking": {
        "url": os.getenv("MCP_SEQUENTIAL_THINKING", "http://sequential-thinking:8085/mcp"),
        "enabled": True,
        "description": "Sequential Thinking Engine v2.0 - Step-by-step reasoning with CIM validation",
    },

    # ─────────────────────────────────────────────────────────────
    # CORE: CIM Server - Frank's Causal Intelligence Module (NEU!)
    # ─────────────────────────────────────────────────────────────
    "cim": {
        "url": os.getenv("MCP_CIM", "http://cim-server:8086/mcp"),
        "enabled": True,
        "description": "Causal Intelligence Module - Graph building, validation, anti-pattern detection",
    },

    # ─────────────────────────────────────────────────────────────
    # CORE: Skill Server - AI Skill Management & Creation
    # ─────────────────────────────────────────────────────────────
    "skill-server": {
        "url": os.getenv("MCP_SKILL_SERVER", "http://trion-skill-server:8088"),
        "enabled": True,
        "description": "AI Skill Studio - Create, validate and manage skills",
    },

    # ─────────────────────────────────────────────────────────────
    # CORE: Storage Broker - Storage governance / policy broker
    # ─────────────────────────────────────────────────────────────
    "storage-broker": {
        "url": os.getenv("MCP_STORAGE_BROKER", "http://storage-broker:8089/mcp"),
        "enabled": os.getenv("ENABLE_MCP_STORAGE_BROKER", "true").lower() == "true",
        "description": "Storage governance broker (disk discovery, zones, policy, audit)",
    },
    
    # ─────────────────────────────────────────────────────────────
    # CORE: System-Addons - TRIONs dynamisches Selbstwissen (Artifact Registry)
    # ─────────────────────────────────────────────────────────────
    "system-addons": {
        "url": os.getenv("MCP_SYSTEM_ADDONS", "http://system-addons:8090/mcp"),
        "enabled": os.getenv("ENABLE_MCP_SYSTEM_ADDONS", "true").lower() == "true",
        "description": "Artifact Registry — TRIONs selbst erstellte Skills, Cron-Jobs und Konfigurationen",
    },

    # ─────────────────────────────────────────────────────────────
    # DEMO: Time MCP
    # ─────────────────────────────────────────────────────────────
    "time-mcp": {
        "command": "python3 -u /app/custom_mcps/time-mcp/server.py",
        "transport": "stdio",
        "path": "/app/custom_mcps/time-mcp",
        "enabled": os.getenv("ENABLE_MCP_TIME_MCP", "true").lower() == "true",
        "description": "Simple Time MCP (STDIO, configurable timezone/country/region)",
    },


}


def get_enabled_mcps() -> Dict[str, Dict[str, Any]]:
    """Gibt nur aktivierte MCPs zurück."""
    return {
        name: config 
        for name, config in MCPS.items() 
        if config.get("enabled") and (config.get("url") or config.get("command"))
    }


def get_mcps() -> Dict[str, Dict[str, Any]]:
    """Backward-compatible full MCP registry snapshot."""
    return dict(MCPS)


def get_mcp_config(name: str) -> Dict[str, Any]:
    """Gibt Config für ein spezifisches MCP zurück."""
    return MCPS.get(name, {})


def list_core_mcps() -> list:
    """Listet alle Core MCPs auf (immer enabled)."""
    return ["sql-memory", "sequential-thinking", "cim"]
