---
Tags: [TRION, Layer-3, Architektur]
aliases: [Layer 3, OutputLayer, core/layers/output.py]
---

# 🗣️ Layer 3: Output (`core/layers/output.py`)

> [!info] Zusammenfassung
> Das ist absolut die komplexeste und massivste Datei im ganzen Core (fast 3300 Zeilen!). Hier passiert weit mehr als nur "Text für den User hübsch formatieren".

Die Kernaussage im Docstring verrät schon das Problem: *"Native Ollama Tool Calling... Automatic tool loop"*. Das Output-Layer ruft nicht nur einmal das LLM auf, sondern **agiert selbst als vollautomatischer Agent**.

**Was positiv ist:**
- Es holt sich wunderbar die "Persona" (den Charakter) des Assistenten, berechnet dynamisch Token-Budgets und fügt die "Warnings" des [[Control]]-Layers clever ein.
- Es bereitet die "Grounding Evidence" (Beweise/Ergebnisse) sehr detailliert für das LLM vor.

---

## ⚠️ Architektur-Probleme im Output

Das Output-Setups hat das massivste Architektur-Problem des Gesamtsystems:

> [!warning] 1. Ein Agent im Output-Layer (Bruch der Single Control Authority)
> Eigentlich ist das System so designt, dass die Ausführung durch den Executor passiert. Aber Layer 3 schaltet einen "Native Tool Loop" frei. Es durchläuft Schleifen (bis zu 5x), ruft eigenmächtig Tools vom MCP Hub ab und besorgt sich Ergebnisse an [[Layer 2 (Control)]] vorbei.

> [!warning] 2. Hardcoded Prompt-Templates tief im Code
> Funktionen wie `_build_container_prompt_rules` bauen hunderte Zeilen spezifischer Container- und Skill-Prompts (`"Die Antwort MUSS mit dem Literal 'Laufende Container:' beginnen"`). Dies gehört in Text-Vorlagen oder RAG-Module, nicht in die Runtime-Klasse.

> [!warning] 3. Manueller String-Parser für Tool-Karten
> Das Layer parst mühsam händisch Texte (`[TOOL-CARD:]`) durch String-Matching, um Speicher-Ergebnisse zu lesen.

---

## 🕸️ Verbindungen nach außen

Layer 3 ist fast mit dem kompletten System verdrahtet:

**Inbound (Wer ruft es auf?):**
- [[Orchestrator]] zum Schluss, nachdem (eigentlich) alle Tools bereits ausgeführt wurden.

**Outbound (Was ruft es auf?):**
- `core.llm_provider_client`: Baut native Chat-Verbindungen (für die Tool-Loop-Unterstützung).
- `mcp.hub` / `mcp_registry`: Zieht sich eigenmächtig verfügbare Tools rein, um sie an das Output-LLM zu hängen.
- `core.plan_runtime_bridge` & `core.control_contract`: Um die Sicherheitsentscheidungen abzuholen.
- `core.grounding_policy`: Zieht sich die RAG/Evidence-Daten.
- `core.persona`: Zieht sich die Identität, wie der Assistent klingen soll.

---

> [!abstract] Gesamtfazit über 4-Layer-Struktur
> Die Grundidee der 4 Layer ist brillant. In der Praxis wurde sie aber aufgeweicht:
> - **Control** rechnet in Python nach, weil es LLMs nicht traut.
> - **Thinking** hat Hardcode-Skills, weil es Loader-Modulen nicht traut.
> - **Output** agiert wieder als Executor, um moderne Features wie Native-Tool-Calling zu nutzen.
> 
> Dies sind die besten Ansatzpunkte für zukünftige Refactorings!