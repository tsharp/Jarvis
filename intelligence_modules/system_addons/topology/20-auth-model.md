---
id: system-auth-model
title: Auth-Modell im TRION-System
scope: auth_model
tags:
  - auth
  - token
  - credentials
  - secrets
  - bearer
  - zugriff
priority: 80
retrieval_hints:
  - auth
  - token
  - credentials
  - zugriff
  - bearer
  - secret resolve
  - zugriffsmodell
  - wie authentifiziere
  - interner token
confidence: high
last_reviewed: 2026-04-21
---

## Invarianten

- Auth-Regel != Live-Konfiguration.
- Diese Datei beschreibt Zugriffsmodell, nicht aktuelle Reachability.
- Secret-Werte sind nie ausgabefähig.
- Interne Docker-Kommunikation ist nicht automatisch öffentlich.
- Resolve-sensitive Endpoints sind nicht als externe Standardpfade zu behandeln.

## Auth-Zonen

| zone | regel |
|---|---|
| docker_internal_trust | interne Service-zu-Service-Kommunikation im Docker-Netz |
| token_guarded_secret_resolve | Secret-Klartextauflösung braucht Bearer-Token |
| proxy_exposed | bestimmte Services sind extern via nginx/proxy erreichbar |
| tool_guarded_access | operative Nutzung bevorzugt über Tools statt rohe Direktcalls |

## Secret-Endpoints

| endpoint | auth | netzregel | ausgabe |
|---|---|---|---|
| `GET /api/secrets` | kein Klartext-Secret-Auth | intern bevorzugt | nur Namen |
| `GET /api/secrets/resolve/{NAME}` | Bearer `INTERNAL_SECRET_TOKEN` | Docker-Netz-only, nicht via nginx | Klartext-Secret |
| Admin-API → MCP `secret_save` | interner Call | Docker-Netz | persistiert verschlüsselt |

## Allgemeine Regeln

- `jarvis-admin-api` ist für interne Calls grundsätzlich Docker-intern vertrauensbasiert.
- Secret-Resolve ist die explizite Ausnahme mit zusätzlichem Bearer-Schutz.
- Resolve-Endpoint ist sensitiv, auch wenn Name bekannt ist.
- Secret-Namen sind weniger sensitiv als Secret-Werte, aber nicht frei publizierbar.

## Skill-Regeln

- Skills sollen Secrets über `get_secret("NAME")` beziehen.
- `get_secret("NAME")` kapselt Namensnormalisierung, Resolve und Alias-Fallback.
- Skill-Code soll keine Secret-Werte hardcoden.
- Skill-Code soll keine Secret-Werte aus normalen Dateien oder freier Env lesen.
- Skill-Code soll Secret-Werte nicht loggen, nicht printen, nicht zurückgeben.

## Nie nach außen geben

- Secret-Werte
- Bearer-Token für Secret-Resolve
- Authorization-Header
- API-Key-Strings
- Klartext-Secrets in Tool-Trace
- Klartext-Secrets in Chat-Antworten
- Klartext-Secrets in Exceptions oder Debug-Logs

## Offen vs. intern

| bereich | außen_geeignet | intern_only |
|---|---|---|
| normale UI/API-Nutzung | ja | nein |
| Secret-Namen listing | eingeschränkt | bevorzugt intern |
| Secret-Klartext resolve | nein | ja |
| operative Secret-Nutzung | nein | ja |
| rohe interne Resolve-URLs als Nutzerpfad | nein | ja |

## Zugriff

- Für Secret-Verwendung in Skills: `get_secret("NAME")`.
- Für Secret-Inventar: `GET /api/secrets` oder entsprechende interne Tool-Pfade.
- Für Klartext-Resolve: nur intern, nur mit Bearer, nur wenn operativ nötig.
- Für normale Agentenentscheidungen erst read-only Pfade bevorzugen.

## Grenzen

- Diese Datei sagt nicht, ob ein Token aktuell gesetzt ist.
- Diese Datei sagt nicht, ob nginx aktuell einen Pfad exponiert.
- Diese Datei sagt nicht, ob ein Endpoint aktuell erreichbar ist.
- Diese Datei erlaubt nie die Ausgabe von Secret-Werten.
