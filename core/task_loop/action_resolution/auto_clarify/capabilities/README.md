# Auto Clarify Capability Handlers

Dieses Paket enthaelt die domain-spezifischen Handler fuer `auto_clarify/`.

Ziel:
- pro Capability-Familie festlegen, welche fehlenden Informationen TRION
  selbst entdecken oder ergaenzen darf
- die generischen Safety-Gates aus dem Parent-Paket wiederverwenden
- keine generische Loop-Core-Logik hier ablegen

Geplante Handler:
- `container.py`
- `skill.py`
- `cron.py`
- `mcp.py`
- `generic.py`
