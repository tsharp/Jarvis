---
Tags: [TRION, Architecture, RAG, CIM, Intelligence]
aliases: [CIM, Causal Intelligence Module, intelligence_modules]
---

# 🧠 Causal Intelligence Module (CIM)

Das **Causal Intelligence Module (CIM)**, zu finden unter `/intelligence_modules/`, ist das fortschrittlichste externe Wissens- und Logik-System innerhalb von TRION. Entwickelt von *Agentarium*, verfolgt es das Ziel, LLMs von reiner "Mustererkennung" (Association) auf echte **kausale Inferenz** (Ursache-Wirkung / "What if?") anzuheben.

## 🏗️ 1. Architektur des CIM

Das System basiert auf einer 3-stufigen **Snowball Retrieval Pipeline**:

1. **Knowledge RAG:** 
   Identifiziert sogenannte "First Principles" und baut Graphenketten (DAGs - Directed Acyclic Graphs). Es gibt dem LLM den grundlegenden fachlichen Kontext.
2. **Procedural RAG:** 
   Injiziert validierte Denk-Templates (wie geht das System mit Problemen um?) und schaltet "Anti-Pattern"-Warnungen vor (z. B. Schutz vor dem Simpson-Paradoxon).
3. **Executable RAG:** 
   Verbindet das LLM mit einer `causal_math_registry`. Die Idee: Das LLM *denkt* nur, aber die tatsächliche Mathematik und Wirkungsberechnung wird deterministisch von Python-Code übernommen.

## ⚙️ 2. Die Datei `cim.py` (Der Gatekeeper)

Die Datei `cim.py` agiert als CLI/Gatekeeper für dieses Modul. Wenn ein User-Prompt in TRION speziell geflaggt ist (z. B. durch `/c` oder `/causal` am Anfang), greift dieses Modul direkt ein. 

Es besitzt verschiedene `GraphBuilder`-Modi:
- `light`
- `heavy`
- `strategic`
- `temporal`
- `simulation`

Zusätzlich kann es dynamisch **Mermaid-Graphen** erstellen (`-v`) oder den Output als hoch-spezielles LLM-Prompt verpacken (`-p` / `CausalPromptEngineer.engineer_prompt`). 

Jeder Causal-Aufruf wird zudem in einem dedizierten `/logs/causal_traces/` Audit-Log gespeichert.

---

## ⚠️ 3. Identify Technical Debt: Das Architektur-Problem mit TRION

> [!warning] Architecture Smell: Doppelter Boden (Layer 1 vs. CIM)
> Obwohl das CIM dieses riesige, potente RAG-System besitzt, haben wir in der `config.py` und in `Layer 1 (Thinking)` gesehen, dass der Orchestrator trotzdem eigene Prompts hartkodiert, um Container- oder System-Wissen beizubringen.

**Das eigentliche Problem:**
Das CIM ist im Grunde ein *"Agent in einer Box"*. TRION nutzt dieses Modul zwar als RAG-Backend für `container_addons` und `skill_addons` (gesehen in `core/orchestrator_modules/context/semantic.py`), aber vertraut ihm nicht vollständig das Lenkrad (Control Authority) für die Kausalität an.

**Refactoring-Plan:**
Um die harte Kopplung in `Layer 1` zu lösen, sollte das CIM als die **einizge** Prompt-Engineering-Instanz (über sein `procedural_rag`) für spezifische Denkprozesse genutzt werden. Layer 1 sollte dumm bleiben und nur sagen: *"CIM, gib mir deinen Causal-Prompt für dieses Nutzer-Szenario"*, anstatt eigene Regeln in der globalen Konfiguration zu pflegen.
