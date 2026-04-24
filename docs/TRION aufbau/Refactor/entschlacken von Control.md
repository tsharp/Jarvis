---
Tags: [TRION, Refactoring, Layer-2, Security]
aliases: [Control Refactoring, entschlacken von Control]
---

# 🧹 Refactoring-Idee: Entschlacken von [[Control]]

Im [[Control]] Layer (`core/layers/control.py`) gibt es aktuell extrem viel hartcodierte Python-Sicherheitslogik. Langfristig sollte diese isoliert werden ("Separation of Concerns").

Hier ist eine Übersicht der aktuellen Fremdlogiken im Code:

## 🔍 1. Aktuelle Fremdlogiken in Control

> [!warning] 1. Hardcoded Regex Command-Scanner (Zerstörungsschutz)
> Bevor oder nachdem das LLM überhaupt etwas sagt, jagen `_user_text_has_hard_safety_keywords` und `_user_text_has_malicious_intent` Regex-Muster über den Text. Blockiert wird **strikt per Code** bei:
> - Zerstörerischen Konsolen-Befehlen: `rm -rf /`, `sudo rm -rf`, `mkfs.*`, `format [a-z]:`
> - Dateilöschungen in Masse: `delete all files`, `alle dateien loesch`

> [!warning] 2. Malicious Intent Lexika (Hacker- & Viren-Schutz)
> Python betätigt den Not-Aus bei Verben und Namen wie:
> - `hacke`, `hacken`, `exploit`, `crack`
> - `virus`, `malware`, `trojan`, `botnet`
> - `passwort ausliest`, `stehlen`, `exfiltriert`

> [!warning] 3. PII (Personal Identifiable Information) Notbremse
> In `_infer_block_reason_code` wirft Regex blitzschnell einen Hardware-Block bei sensiblen Daten (`password`, `api key`, `token`).

> [!warning] 4. Hardware Self-Protection Guard
> Der Schalter `hardware_gate_triggered` führt zu einem Block aus Grund `hardware_self_protection`.

> [!warning] 5. Der Hard-Block-Polizist (`_enforce_block_authority`)
> Gleicht die Blockier-Gründe des LLMs gegen `DEFAULT_HARD_BLOCK_REASON_CODES` ab. Hat das LLM einen "Fantasie-Grund" erfunden, ändert Python die Entscheidung hart auf "Warnung".

---

## 🛠️ 2. Der Refactoring-Plan

Anstatt alles als "Utils" zu deklarieren, bietet sich ein dedizierter Ordner `core/safety/` oder `core/policy/` an. Hier sind Vorschläge für sehr sprechende Modulnamen:

### `lexical_guard.py` oder `threat_scanner.py`
Hier wandert alles rein, was reiner Text-Musterabgleich (Regex) ist.
- **Funktionen:** `scan_for_destructive_commands()`, `scan_for_malicious_intent()`

### `pii_detector.py`
Trennt die Bedrohung gegen das System von der Bedrohung der Nutzerdaten.
- **Funktionen:** `contains_sensitive_data()`, `has_credential_leaks()`

### `false_positive_resolver.py` oder `spurious_block_lifter.py`
Das ist reines Domain-Wissen: Die Regeln, wann man Container und Cronjobs doch durchwinken darf, obwohl das LLM Angst hatte.
- **Funktionen:** `should_lift_container_block()`, `evaluate_cron_exception()`

### `authority_enforcer.py` oder `strict_policy_enforcer.py`
Dieser Boss zwingt das abstrakte LLM-Gemurmel in einen echten Machine-State ("Ja" oder "Nein").
- **Funktionen:** `enforce_approved_reason_codes()`, `downgrade_to_warning_if_invalid_reason()`

---

## ✨ 3. Wie sähe `control.py` danach aus?

Anstatt 2300 Zeilen voller Regex-Listen wäre `control.py` fast leer und extrem lesbar:

```python
# 1. Schneller Text-Check vor dem LLM
if threat_scanner.has_direct_threat(user_text) or pii_detector.contains_secrets(user_text):
    return create_hard_block("malicious_intent_or_pii")

# 2. LLM Fragen
llm_decision = await stream_chat(prompt)

# 3. LLM-Fehler (irrtümliche Blocks) korrigieren
llm_decision = false_positive_resolver.correct_spurious_blocks(llm_decision, thinking_plan)

# 4. Final durchsetzen
final_decision = authority_enforcer.finalize_decision(llm_decision)

return final_decision
```en

final_decision = authority_enforcer.finalize_decision(llm_decision)

return final_decision