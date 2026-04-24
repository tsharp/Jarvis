---
Tags: [TRION, Refactoring, Roadmap]
aliases: [Master Plan, Refactoring Roadmap]
---

# 🗺️ Master Refactoring Plan

Basierend auf unserer System-Analyse aller 10 Domänen von TRION haben wir einen klaren Pfad zur Entschuldung (Technical Debt Resolution) der Architektur erarbeitet. Das Ziel ist es, von "klein nach groß" aufzuräumen.

## Phase 1: Die Config entwurzeln
- **Fokus:** `config.py` (58 KB God-File)
- **Problem:** Alle Systemvariablen, Konstanten und Fallbacks liegen kreuz und quer in einer Datei.
- **Lösung:** Migration auf stark typisierte `pydantic-settings`. Aufsplittung in `DatabaseSettings`, `PathSettings`, `OllamaSettings` etc.

## Phase 2: Zirkuläre Abhängigkeiten kappen (Layer 0)
- **Fokus:** `utils/`
- **Problem:** Helper-Skripte wie `ollama_endpoint_manager.py` wissen Dinge über den `container_commander`. Das ist eine Layer-Violation.
- **Lösung:** Dependency Injection. Helper-Funktionen bekommen die Container-Infos per Argument übergeben und holen sie sich nicht selbst.

## Phase 3: Die Persona-Psychologie modernisieren
- **Fokus:** `personas/` & `core/persona.py`
- **Problem:** Eigener Text-Parser für ein INI-ähnliches Format, unflexibel für neue Features. Hardkodierte Container-Regeln im Python-Code,
- **Lösung:** Umstieg auf `YAML`. Domain-spezifische Prompts sollen künftig vom jeweiligen MCP-Tool live injiziert werden, statt im Basis-Code zu stehen.

## Phase 4: Die MCP-Registry bereinigen
- **Fokus:** `mcp_registry.py` & `mcp/`
- **Problem:** Veraltete, hartkodierte Tool-Trigger und JSON-Schemata. Doppelte Buchführung trotz des modernen MCP-Hubs.
- **Lösung:** Vertrauen auf Dynamic Discovery. Alle statischen Tool-Definitionen in Python fliegen raus.

## Phase 5: Das SQL-Memory skalieren
- **Fokus:** `sql-memory/vss.py`
- **Problem:** Python iteriert über Tausende Vektoren mit For-Schleifen zur Ähnlichkeitsberechnung. Das wird sehr schnell extrem langsam.
- **Lösung:** Einbau von nativen SQLite Vector-Search Extensions (`sqlite-vec`).

## Phase 6: Den Orchestrator entflechten (Endgegner)
- **Fokus:** `core/orchestrator.py`
- **Problem:** Die orchestrierende KI macht RAG, Docker, Temporal Parsing und Hardware-Monitoring gleichzeitig (Verletzung des Single Responsibility Principle).
- **Lösung:** Umbau des Orchestrators zu einem reinen "Router". Jedes Domain-Wissen wandert in dedizierte Plugins aus.
