---
Tags: [TRION, Layer-1, Architecture]
aliases: [Layer 1, ThinkingLayer, core/layers/thinking.py]
---

# 🧠 Layer 1: Thinking (`core/layers/thinking.py`)

> [!info] Zusammenfassung
> Das Layer 1 ist deutlich größer und komplexer als der [[Tool Selector]]. Seine Hauptaufgabe: Den Input lesen, live über ein LLM (meist DeepSeek-R1) "überlegen" und strukturierte Parameter (den Action-Plan / JSON) zurückgeben. 

**Was positiv ist:**
- Es ist vorbildlich geschrieben für das asynchrone **Live-Streaming** ins Frontend (zeigt das "Überlegen" des Modells dem Nutzer live an, bevor der fertige JSON-Plan steht).
- Sauberes Error-Handling und stabiler Fallback (liefert den `_default_plan()`, damit das System nicht crasht).
- Das extrahierte Plan-Format (JSON) ist hochstrukturiert: Intents, Memory-Bedürfnis, Tonalität, Komplexität, Sequentielles Denken.

---

## ⚠️ Architektur-Reibungspunkte

Man merkt deutlich, dass das System schnell gewachsen ist. Es gibt drei große Verstöße gegen saubere `Separation of Concerns`:

> [!warning] 1. Starkes Overfitting ("Coupling") im Prompt
> Der hartkodierte `THINKING_PROMPT` im Code ist randvoll mit extrem spezifischem Wissen über Unter-Systeme ("Container Commander Tools", `exec_in_container`, `blueprint_list`). Wenn jemand den Container-Service umschreibt, bricht Layer 1. Das sollte abstrahiert werden (z.B. durch `intelligence_modules`).

> [!warning] 2. Infrastruktur-Routing im Mental-Layer
> Das Skript kümmert sich um Endpoint-Auflösung (`resolve_role_endpoint`) und Hard-Error-Handling für nicht erreichbare Ollama-Instanzen. Das gehört eigentlich in einen abstrakten API-Client.

> [!warning] 3. Vorbeischummeln an der Hierarchie (MCP Hub Zugriff)
> Das Layer holt sich mittels `get_hub().get_system_knowledge(...)` selbst dynamische Regeln für Tools ab. Eigentlich sollte der [[Orchestrator]] diese Kontext-Infos vorab zusammenbauen und als Argument hineinreichen.

---

## 🕸️ Verbindungen nach außen

Layer 1 ist ein Knotenpunkt-Heavyweight.

**Inbound (Wer ruft es auf?):**
- [[Orchestrator]] (`PipelineOrchestrator`): Gibt `user_text`, `memory_context`, verfügbare Tools und Tone-Signals hinein.

**Outbound (Was ruft es auf?):**
- `core.llm_provider_client`: Feuert den Prompt tatsächlich gegen die LLM-Schnittstelle ab (`stream_prompt`).
- `utils.role_endpoint_resolver`: Löst Infrastruktur-Pfade für das Modell auf.
- `mcp.hub`: Zieht sich über einen Seiteneingang dynamische "Detection Rules" direkt aus der Tool-Umgebung.
- `config`: Holt Grundeinstellungen wie das primäre Thinking-Model.
- `utils.json_parser`: Bereitet den Output lesbar für den Orchestrator auf.

> [!abstract] Fazit
> Layer 1 macht seinen Job sehr robust, ist aber extrem verwoben mit Infrastruktur-Details und hartkodiertem Wissen über Container und Skills, das eigentlich abstrahiert werden müsste, falls das Projekt skaliert.