---
id: trion-home-runtime
title: TRION Home Runtime
scope: runtime
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
tags:
  - python
  - debian
  - slim
  - runtime
priority: 95
retrieval_hints:
  - python version
  - package manager
  - what is installed
  - install package
  - pip
  - apt
  - runtime environment
  - init system
commands_available:
  - python3
  - pip
  - pip3
  - apt-get
  - bash
  - sh
  - ls
  - cat
  - echo
  - mkdir
  - cp
  - mv
  - rm
  - find
  - grep
  - curl
  - wget
  - base64
  - date
  - env
confidence: high
last_reviewed: 2026-04-01
---

# Summary

Schlankes Debian-Image mit Python 3.12. Kein Init-System, kein Desktop, keine Dienste.
PID 1 ist der direkt gestartete Prozess — bei exec-Kommandos meist `bash` oder `sh`.

## Environment

- **PID 1**: kein Init — direkt gestarteter Prozess
- **Python**: `python3.12` (systemweit, kein venv by default)
- **Package Manager (Python)**: `pip` / `pip3`
- **Package Manager (System)**: `apt-get` (Debian slim)
- **Shell**: `bash` und `sh` verfügbar
- **Netzwerk**: nur intern — kein Internetzugang für `pip install` oder `apt-get`

## Wichtig: Netzwerk

Der Container läuft im `internal`-Netzwerk.
`pip install` und `apt-get install` funktionieren **nicht** ohne Host-Netzwerk.
Pakete müssen entweder vorinstalliert oder über den Host bereitgestellt werden.

## Was vorinstalliert ist (python:3.12-slim Basis)

- `python3`, `pip`, `pip3`
- `bash`, `sh`, `cat`, `ls`, `mkdir`, `cp`, `mv`, `rm`, `find`, `grep`
- `curl`, `wget`
- `base64`, `date`, `env`, `echo`
- Standard-Python-Stdlib (vollständig)

## Was fehlt

- Kein `git`
- Kein `vim` / `nano` (nur `cat`/`echo` für Dateiediting)
- Kein `jq`
- Kein `systemctl`, `service`, `supervisorctl`
- Keine GUI, kein Display

## Wichtige Befehle

```bash
# Python-Version prüfen
python3 --version

# Installierte Pakete
pip list

# Script ausführen
python3 /home/trion/scripts/myscript.py

# Datei schreiben (kein vim — base64 oder echo verwenden)
echo "inhalt" > /home/trion/notes/test.txt

# Verzeichnisinhalt
ls -la /home/trion/

# Prozesse (minimal — kein htop)
ps aux
```

## Prefer

- Python für komplexere Logik — nicht Bash.
- `pip list` vor Paketnutzung prüfen ob es installiert ist.
- Dateien immer unter `/home/trion/` ablegen — nur dort persistent.

## Avoid

- `apt-get install` ohne Prüfung ob Netzwerk verfügbar ist.
- Annahme dass externe Pakete vorhanden sind ohne `pip list` zu prüfen.
- Dateien außerhalb `/home/trion/` ablegen — sie gehen beim Neustart verloren.
