---
Tags: [TRION, Layer-0, Architecture]
aliases: [Layer 0, ToolSelector]
---

# 🔭 Layer 0: Tool Selector (`tool_selector.py`)

Generell ist das Skript erfreulich kompakt (`~140 Zeilen`) und tut genau eines: Es filtert via Vector-Ähnlichkeit (`memory_semantic_search`) Tool-Kandidaten vor, ganz ohne teure LLM-Aufrufe.

**Was positiv ist:**
- Es parst sauber Metadaten und Ähnlichkeitswerte (`_extract_similarity`).
- Es unterscheidet korrekt zwischen `tool_X` und `skill_X`.
- Es hat sinnvolle Fallbacks für Fehlerbehandlung.

---

## ⚠️ Architektur-Hacks (Technical Debt)

Es gibt zwei bis drei "Pragmatismus-Hacks", die architektonisch eigentlich an eine andere Stelle gehören:

> [!warning] 1. Der Context-Enrichment Hack
> Es gibt eine Logik: *Wenn der Input weniger als 5 Wörter hat (z. B. "ja bitte"), klatsche den vorherigen Kontext hinten dran.* Das ist nützlich, vermischt aber Such-Logik mit "Kontext-Management". Streng genommen müsste der [[Orchestrator]] den Such-String so aufbauen, nicht der Such-Algorithmus selbst.

> [!warning] 2. Startup Race-Condition Workaround
> Es gibt Logik, um `self.hub.refresh()` aufzurufen, falls das `memory_semantic_search` Tool noch fehlt. Das ist ein "Pflaster" für Timing-Probleme direkt beim Start, das eigentlich ins Lifecycle-Management des Event-Hubs gehört.

> [!warning] 3. Synchrones Fallback-Gewurschtel
> Er prüft via `hasattr(self.hub, "call_tool_async")`, ob er modern aufrufen kann, oder wrappt es in `asyncio.to_thread`. Das gehört eigentlich als Abstraktion ins `mcp.hub`.

*(Alles völlig legitim für ein wachsendes System und stört die Funktion nicht, aber in einer reinen Systemarchitektur sind das "Fremdkörper".)*

---

## 🕸️ Verbindungen nach außen

Der Tool Selector hat ein sehr enges Netz:

**Inbound (Wer ruft ihn auf?):**
- [[Orchestrator]] (`PipelineOrchestrator`): Instanziiert den Selector und reicht ihm den Nutzertext und den Summary-Kontext hinein.

**Outbound (Was ruft er auf?):**
- `config`: Hart gekoppelt an die Flags `ENABLE_TOOL_SELECTOR`, Candidate Limits und Min-Similarity.
- `mcp.hub`: Greift sich direkt den zentralen Tool-Hub (`get_hub()`).
- `memory_semantic_search`: Das explizite System-Tool (bereitgestellt durch `sql-memory`), gegen das er die tatsächlichen Suchanfragen feuert.

> [!abstract] Kurzfassung
> Er sitzt komplett eingeklemmt zwischen dem Config, dem **Orchestrator** (als Auftraggeber) und dem **MCP Hub** (als Adressbuch / Ausführungsschnittstelle für das Memory-Tool).