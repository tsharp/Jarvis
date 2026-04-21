---
id: system-alias-model
title: Secret-Alias-Modell im Skill-Runner
scope: alias_model
tags:
  - secrets
  - alias
  - skill-runner
  - get_secret
  - naming
priority: 70
retrieval_hints:
  - alias
  - key name
  - get_secret
  - test_key test_api_key
  - secret name mapping
  - schlüssel name
  - falscher secret name
  - anderer name im vault
confidence: high
last_reviewed: 2026-04-20
---

# Secret-Alias-Modell

## Summary
Der Skill-Runner löst Secret-Namen automatisch auf wenn der exakte Name nicht
im Vault liegt. Das passiert transparent — der Skill-Code muss nichts anpassen.

## Ablauf in skill_runner.py:344–376

```
get_secret("OPENAI_API_KEY") im Skill-Code
        │
        ▼
1. Exact Match: OPENAI_API_KEY im Vault?
   → ja: Klartext zurückgeben ✅
   → nein: weiter zu Schritt 2

2. Alias-Modus aktiv? (SKILL_SECRET_ALIAS_MODE != "off")
   → nein: "" zurückgeben
   → ja: weiter zu Schritt 3

3. Verfügbare Secret-Namen vom Vault holen
   GET /api/secrets → Liste aller Namen

4. Alias suchen (_find_secret_alias):
   OPENAI_API_KEY → prüfe OPENAI_KEY (Suffix-Swap _API_KEY ↔ _KEY)
   Gefunden → OPENAI_KEY auflösen ✅
   Event: skill_secret_alias_match geloggt
```

## Alias-Regeln (_find_secret_alias, skill_runner.py:164–196)

| Gesuchter Name | Automatisch auch geprüft | Bedingung |
|---|---|---|
| `TEST_API_KEY` | `TEST_KEY` | Suffix `_API_KEY` → `_KEY` |
| `TEST_KEY` | `TEST_API_KEY` | Suffix `_KEY` → `_API_KEY` |
| `OPENAI` (Base) | `OPENAI_API_KEY` oder `OPENAI_KEY` | Nur wenn genau einer existiert |

**Normalisierung:** Alle Namen werden vor dem Vergleich uppercase + trim.

## Konfiguration

```
SKILL_SECRET_ALIAS_MODE=safe    # default: Alias aktiv
SKILL_SECRET_ALIAS_MODE=off     # Alias deaktiviert, nur exact match
```

## Konsequenzen für Skill-Entwicklung

- Im Vault liegt `OPENAI_KEY` → Skill kann `get_secret("OPENAI_API_KEY")` schreiben ✅
- Im Vault liegt `OPENAI_API_KEY` → Skill kann `get_secret("OPENAI_KEY")` schreiben ✅
- Kein manuelles Mapping nötig
- Bei zwei Kandidaten (OPENAI_KEY + OPENAI_API_KEY) gewinnt exact match

## Grenzen

- Alias-Auflösung läuft **nur im Skill-Runner-Kontext** (tool-executor)
- TRION selbst hat keinen Zugriff auf Klartext-Werte — nur der Skill-Code
- `list_secret_names` zeigt die rohen Vault-Namen — TRION sieht z. B. `OPENAI_KEY`
  und kann daraus ableiten dass ein Skill `get_secret("OPENAI_API_KEY")` schreiben darf
