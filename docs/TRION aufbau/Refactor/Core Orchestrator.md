---
Tags: [TRION, Architecture, Core, Orchestrator]
aliases: [PipelineOrchestrator, core]
---

# 🧠 Core & Orchestrator (Das Zentralhirn)

Wir haben den Endgegner der Architektur erreicht: Das Verzeichnis `core/`.
Hier liegt das Herz von TRIONs **3-Layer Execution Pipeline**, orchestriert von einer extrem massiven Architektur, die hunderte Sub-Routinen steuert.

## 🏗️ 1. Die Architektur: 3-Layer Pipeline

Die Haupt-Klasse `PipelineOrchestrator` (`core/orchestrator.py`) steuert den synchronen und asynchronen (stream) Lebenszyklus jeder einzelnen User-Nachricht durch drei K.I.-Ebenen:

1. **Thinking Layer (`core/layers/thinking.py`):** 
   - Meist angetrieben durch ein Planungsmodell (z.B. DeepSeek). 
   - Überlegt: "Welche Tools brauche ich? Darf das der Nutzer? Muss ich Daten zwischen Tools weiterreichen?"
2. **Control Layer (`core/layers/control.py`):** 
   - Die Polizei-K.I. (meist Qwen).
   - Verifiziert den Plan: Sind die Parameter sicher? Gibt es einen Hardware-Engpass? Die Layer hat Veto-Recht!
3. **Output Layer (`core/layers/output.py`):** 
   - Konsumiert die echten Tool-Ergebnisse und spricht final in der Persona mit dem User.

## ⚠️ 2. Identify Technical Debt: Der God Class Pattern

Der `core/`-Ordner besteht aus sage und schreibe **89 einzelnen Dateien**, und die `orchestrator.py` selbst ist **115.000 Bytes (2.800+ Zeilen)** groß. 
Darüber hinaus gibt es Helper-Dateien (z.B. `orchestrator_stream_flow_utils.py`), die sogar 126.000 Bytes umfassen.

> [!danger] Architecture Smell: Monolithischer Orchestrator
> Die Orchestrator-Klasse importiert buchstäblich das gesamte Universum des TRION-Projekts. Sie kümmert sich um:
> - Hardware Limits prüfen (`_check_hardware_gate_early`)
> - RAG & Context Management (`build_effective_context`)
> - Docker Container State (`_remember_container_state`)
> - Temporal Intents ("Wann ist was passiert?")
> - Budget-Limits für Queries (`QueryBudgetHybridClassifier`)
> 
> Das verletzt extrem das **Single Responsibility Principle**. Ein Orchestrator sollte nur delegieren (Schritt A, dann Schritt B), aber keine State-Management-Regeln von Docker-Containern in sich tragen!

## 🧩 Fazit des Scans

TRION ist kein einfaches Wrapper-Skript, sondern ein hochkomplexes, dezentrales, multi-agentisches KI-Betriebssystem. 
Die größten Baustellen für das anstehende Refactoring sind nun absolut klar:
1. **Config.py**: Die 58.000 Bytes God-File in saubere Settings spalten.
2. **Persona Parser**: Händisches Text-Parsing der Psychologie durch `YAML` + `pydantic` ersetzen.
3. **Utils-Layer Isolation**: Die zirkuläre Abhängigkeiten ("Layer 0" greift auf "Layer 3") auflösen.
4. **Orchestrator Entschlackung**: Domain-Logik (wie Docker/Container-Management) aus dem Orchestrator in unabhängige Plugins/Module verlagern.
