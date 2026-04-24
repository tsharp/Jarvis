---
Tags: [TRION, Layer-2, Architecture, Security]
aliases: [Layer 2, ControlLayer, core/layers/control.py]
---

# 🛡️ Layer 2: Control (`core/layers/control.py`)

> [!info] Zusammenfassung
> Layer 2 ist ein echtes Schwergewicht (~2350 Zeilen) und erfüllt die Rolle der **Policy Authority** – der ultimative Türsteher des Systems. Hier prallen probabilistisches LLM (Qwen/Deepseek) und deterministische Python-Sicherheitsregeln aufeinander.

Die Hauptaufgabe ist es, den Plan aus [[Thinking]] zu nehmen, Sicherheitsregeln anzuwenden und eine final verbindliche JSON-Antwort zu generieren (`approved`, `hard_block`, `corrections`).

**Was positiv ist:**
- Die Architektur ist extrem defensiv und robust (**Zero-Trust**).
- Es gibt klare Schnittstellen (`decision_class: allow/warn/hard_block`), die danach nie wieder in Frage gestellt werden.
- Es bindet `LightCIM` für harte textuelle Keyword-Prüfungen ein (z. B. Regex gegen Befehle wie `rm -rf /`).

---

## ⚠️ Das "Filter-über-den-Filter"-Syndrom

Das Skript ist gefüllt mit extrem viel Fremdlogik und Korrektur-Routinen, weil das Sicherheits-LLM oft false-positives liefert.

Wenn das LLM fälschlicherweise blockiert, rechnen hunderte Zeilen Python-Code händisch nach und "überstimmen" das LLM:
- `_should_lift_cron_false_block()`
- `_should_lift_container_false_block()`
- `_has_solution_oriented_action_signal()`

> [!warning] Architektonisches Problem
> Das LLM wirkt wie eine unsichere Zwischenstufe, deren Hausaufgaben danach von Python-Skripten noch mal korrigiert werden müssen. Langfristig sollten diese LLM-Overrides in ein dezidiertes Python-Sicherheitsregel-Framework ausgelagert werden.
> Siehe auch: [[entschlacken von Control]]

---

## 🕸️ Verbindungen nach außen

Control ist extrem restriktiv verbunden:

**Inbound (Wer ruft es auf?):**
- [[Orchestrator]]: Reicht den fertigen `thinking_plan` (aus Layer 1) zusammen mit dem Nutzer-Text und Memory-Kontext herein.

**Outbound (Was ruft es auf?):**
- `core.control_decision_utils` & `core.control_policy_utils`: Ausgelagerte Logik für Hard-Block-Regeln und Warnungs-Bereinigung.
- `core.safety.LightCIM`: Ein schneller lokaler Keyword-Scanner direkt im Code.
- `intelligence_modules.cim_policy.cim_policy_engine`: Optionales, starkes RAG-Modul zur Erkennung von Causal-Anti-Pattern.
- `core.llm_provider_client`: Die Netzwerk-Schnittstelle, um das Control-LLM aufzurufen.

> [!abstract] Fazit
> Layer 2 ist ein extrem komplexer "Sandwich"-Layer. Es checkt Sicherheit via Python (LightCIM), fragt dann das LLM, und checkt dann das LLM-Ergebnis nochmals per Python ab, um False Positives zu canceln. Es erfüllt seine Rolle als Wächter aktuell mit eiserner Faust, könnte aber durch Auslagern der Python-Regeln deutlich entschlackt werden.