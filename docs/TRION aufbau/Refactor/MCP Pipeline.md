---
Tags: [TRION, Architecture, MCP, Tools, API]
aliases: [MCP Pipeline, mcp_registry, mcp_hub]
---

# 🔌 MCP & Tools Pipeline

Der Model Context Protocol (MCP) Bereich unter `/mcp/` und die `mcp_registry.py` bilden das "Rückenmark" von TRION. Hier werden alle Fähigkeiten (Skills, Memory, Container, Causal Logic) an einem Punkt gebündelt und für das LLM nutzbar gemacht.

## 🏗️ 1. Architektur: Der MCP Hub (`mcp/hub.py`)

Der `MCPHub` ist ein genialer Aggregator:
1. Er liest beim Systemstart die `mcp_registry.py` (welche Microservices laufen, z.B. `cim-server:8086` oder `sql-memory:8081`).
2. Er baut Verbindungen via HTTP, SSE oder STDIO (für lokale Scripte) auf.
3. Er ruft `list_tools()` bei jedem Service auf.
4. **Das Highlight (Auto-Registration):** Sobald er alle Tools kennt, schreibt der Hub ein "Handbuch" seiner eigenen Fähigkeiten als Knoten in TRIONs `sql-memory` (Knowledge Graph). TRION wüsste nicht, was es kann, wenn sich das System nicht beim Hochfahren diese Anleitung selbst ins Gedächtnis schreiben würde!

## ⚡ 2. Die "Fast Lane" Tools

Ein oft auftauchendes Muster im Code ist die **Fast Lane**. 
Normale MCP-Aufrufe haben Overhead (HTTP Requests). Für Tools, die rasend schnell gehen müssen und keine Isolation brauchen (z.B. Dateien lokal im Home-Verzeichnis lesen, Telemetrie-Events loggen), weicht TRION den MCP-Standard per "Fast Lane" auf. Diese Tools werden direkt im Haupt-Python-Prozess des Orchestrators via `FastLaneExecutor` ausgeführt.

---

## ⚠️ 3. Identify Technical Debt: Hardcoding und Redundanz

Auch hier haben wir zwei klassische Architektur-Anti-Patterns gefunden, die durch schnelles Wachstum entstanden sind:

> [!warning] Architecture Smell 1: Doppelte Buchführung in `mcp_registry.py`
> Obwohl der `MCPHub` alle Tools über das standardisierte MCP-Protokoll live von den Endpunkten abfragt (`_discover_tools`), gibt es in `mcp_registry.py` eine riesige Funktion `get_enabled_tools()`, die die Tool-Namen und Beschreibungen für `container-commander`, `sql-memory` und `cim` nochmal als fetten String **hartkodiert**, um sie in den System-Prompt zu pressen. 
> Wenn sich ein Tool im Container-Commander ändert, muss man es aktuell an zwei Orten im Code pflegen!

> [!warning] Architecture Smell 2: Regex & KI
> Im `MCPHub` (`_generate_detection_rules`) gibt es ein massives Dictionary namens `TOOL_KEYWORDS`. Hier stehen Wörter wie `"stoppen", "beenden", "löschen"`. Der Code versucht, aus diesen Wörtern hartkodierte Prompt-Regeln ("Triggers") für Layer 1 zusammenzukleben. Das mischt alte "If-Else"-Spracherkennung mit moderner LLM-Logik.

## 🛠️ 4. Refactoring-Plan

1. **Dry-Prinzip (Don't Repeat Yourself):** Die `get_enabled_tools()` in der Registry muss gelöscht werden. Stattdessen sollte der System-Prompt *nur* dynamisch nach den Tools fragen, die der `MCPHub` beim Start via `list_tools()` live bei den Endpunkten entdeckt hat. Das sorgt sofort für weniger doppelten Code.
2. **Prompts abstrahieren:** Das `TOOL_KEYWORDS`-Dictionary gehört ausgelagert in Prompt-Templates, anstatt im Herzen der API-Logik statische Prompt-Blöcke zu generieren.
