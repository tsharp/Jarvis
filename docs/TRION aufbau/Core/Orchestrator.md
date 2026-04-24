---
Tags: [TRION, Architektur, Orchestrator, Refactoring]
aliases: [PipelineOrchestrator, core/orchestrator.py]
---

# ⚙️ PipelineOrchestrator (`core/orchestrator.py`)

> [!info] Zusammenfassung
> Der Orchestrator ist das "God Object" und Fließband von TRION. Er nimmt die Anfragen entgegen und steuert sie durch die Layer: [[Layer 1 (Thinking)]] ➔ [[Layer 2 (Control)]] ➔ [[Layer 3 (Output)]]. 

**Dateiinfos:**
- **Größe:** ca. 3000 Zeilen (vormals 6000 Zeilen)
- **Besonderheit:** Hat einen massiven Import-Block von ca. 400 Zeilen.

---

## 🔍 1. Architektur & Zustand

Der `PipelineOrchestrator` erfüllt auf dem Papier genau seinen Zweck: Er delegiert den Flow.
Damit die Datei durch die vielen Features nicht explodiert, wurde beim letzten Refactoring das **Strangler-Pattern** (Auslagerung in Utils) angewendet:
- Fast die gesamte Routing-Logik liegt in externen Dateien (`orchestrator_modules...`, `orchestrator_context_...`).
- Die Hauptklasse ist somit heute ein gewaltiger **Adapter/Verteiler**, der Hunderte von Aufrufen an diese externen Utils weiterreicht (Der sogenannte "Utils-Teppich-Trick").

---

## ⚠️ 2. Technical Debt & Domänen-Wissen

Eigentlich sollte ein Orchestrator völlig abstrakt bleiben. In der Praxis ist er aktuell aber stark mit spezifischem Wissen über Use-Cases gekoppelt. 

Folgende "Fremdlogiken" finden sich aktuell im Orchestrator:

> [!warning] 1. Container-State-Verwaltung 
> Der Kern-Orchestrator weiß hartkodiert, was ein "Home Blueprint" ist und beinhaltet Dutzende Methoden nur für Container (z.B. `_resolve_pending_container_id_async`). Ein Orchestrator sollte Tools eigentlich nur als *Blackbox* betrachten.

> [!warning] 2. Auto-Recovery Hokus Pokus
> Es gibt komplexe Methoden wie `_maybe_auto_recover_grounding_once`. Wenn [[Layer 3 (Output)]] fehlende Fakten meldet, greift der Orchestrator aktiv ein und versucht, Daten nachzuladen. Das bricht den linearen Fluss in einen "Kreisverkehr" auf.

> [!warning] 3. Hardware Gates (Vorab-Sicherheitslogik)
> Der Orchestrator fängt Strings wie `"ollama pull"` oder `"65b"` direkt ab (`_HARDWARE_GATE_PATTERNS`). Das ist eigentlich klassische Sicherheitslogik, die in [[Layer 2 (Control)]] oder einen vorgeschalteten `threat_scanner.py` gehört.

---

## 🕸️ 3. Verbindungen nach außen

Das Modul ist das Spinnennetz von TRION und mit (fast) *jedem* Teil des Systems verdrahtet.

**Inbound (Wer ruft ihn auf?):**
- [[CoreBridge]] (`core/bridge.py`): Die Brücke zum Frontend (LobeChat- oder Admin-API).

**Outbound (Wen ruft er auf?):**
- **Die Layer:** [[Layer 1 (Thinking)]], [[Layer 2 (Control)]], [[Layer 3 (Output)]]
- **Tooling:** [[ToolSelector]] (Layer 0), Das Tool Intelligence / MCP Hub System (`mcp.hub`)
- **Klassifizierer:** `ToneHybridClassifier`, `DomainRouterHybridClassifier`
- **Gedächtnis & State:** [[ContextManager]] (holt RAG-Daten)
- **Caches & Policys:** `make_plan_cache`, Container- und Skill-Policies.

---

> [!abstract] Fazit & Nächste Schritte
> Das theoretische 4-Layer-Modell funktioniert sauber. Durch das enorme Feature-Wachstum (Causal Intelligence, Agent-Loops, Blueprints) in den letzten Monaten wurde Code jedoch dort integriert, wo es am schnellsten ging – quer durch den Orchestrator. 
> 
> **Zukunfts-Projekt:** Ein strenges **Separation of Concerns Refactoring**, insbesondere das Kapseln der Python-Sonderlogiken.