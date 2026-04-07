---
id: trion-home-tools
title: TRION Home Tools & Safety
scope: safety
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
tags:
  - tools
  - safety
  - python
  - commands
priority: 85
retrieval_hints:
  - what tools do i have
  - available commands
  - python tools
  - safety rules
  - what should i avoid
  - destructive commands
  - data loss
commands_available:
  - python3
  - pip
  - bash
  - find
  - grep
  - curl
  - base64
confidence: high
last_reviewed: 2026-04-01
---

# Summary

Verfügbare Werkzeuge im TRION Home Container. Python ist das primäre Werkzeug.
Da `/home/trion/` das persistente Zuhause ist, gelten hier erhöhte Vorsichtsregeln.

## Python als Hauptwerkzeug

Python 3.12 mit voller Stdlib. Bevorzugt für:
- Dateiverarbeitung
- Textanalyse und -generierung
- Berechnungen
- Datenstrukturen und Serialisierung (json, csv, yaml via stdlib)
- HTTP-Anfragen (nur intern — `urllib`, kein `requests` by default)

```bash
# Schnelles Python-Oneliner
python3 -c "import json; print(json.dumps({'key': 'value'}, indent=2))"

# Script interaktiv testen
python3 -i /home/trion/scripts/myscript.py

# Stdlib-Module prüfen
python3 -c "import <modul>; print('ok')"
```

## Nützliche Stdlib-Module (immer verfügbar)

| Modul | Verwendung |
|---|---|
| `json` | JSON lesen/schreiben |
| `pathlib` | Dateipfade |
| `datetime` | Datum und Zeit |
| `subprocess` | Shell-Kommandos aus Python |
| `re` | Reguläre Ausdrücke |
| `csv` | CSV-Dateien |
| `urllib` | HTTP-Anfragen (intern) |
| `hashlib` | Hashing |
| `base64` | Encoding |
| `collections` | Counter, defaultdict, deque |
| `itertools` | Iteration |
| `textwrap` | Textformatierung |

## Shell-Werkzeuge

```bash
# Dateien finden
find /home/trion -name "*.py" -type f

# In Dateien suchen
grep -r "suchbegriff" /home/trion/

# Datei-Größen
du -sh /home/trion/*/

# Prozesse
ps aux

# Umgebungsvariablen
env | grep TRION
```

## Verify nach jeder Dateioperation

```bash
# Datei geschrieben?
ls -lh /home/trion/<pfad>
cat /home/trion/<pfad>

# Script läuft?
python3 /home/trion/scripts/<script>.py && echo "OK"
```

## Safety — Vorsichtsregeln für Home

Das Home-Volume ist persistent. Fehler hier wirken nach dem Neustart weiter.

### Vor destructiven Operationen

```bash
# Backup vor rm
cp /home/trion/<datei> /home/trion/<datei>.bak

# Inhalt prüfen vor Überschreiben
cat /home/trion/<datei>
```

### Absolute Grenzen

- `rm -rf /home/trion/memory/` — niemals. Löscht das gesamte Gedächtnis.
- `rm -rf /home/trion/` — niemals. Löscht alles Persistente.
- Skripte die rekursiv in `/home/trion/` schreiben immer zuerst in `experiments/` testen.

## Avoid

- `rm` ohne Prüfung des Pfades — im Home-Container keine Wegwerfumgebung.
- Externe Pakete annehmen ohne `pip list` zu prüfen.
- Endlosschleifen in Scripts ohne Exit-Bedingung — kein Watchdog vorhanden.
- Sensitive Daten (Tokens, Passwörter) in Dateien unter `/home/trion/notes/` oder `/home/trion/journal/` schreiben — Volume ist nicht verschlüsselt.
