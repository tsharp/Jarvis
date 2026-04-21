---
id: system-safe-paths
title: Sichere Selbsterweiterungs-Pfade
scope: safe_paths
tags:
  - selbsterweiterung
  - sicherheit
  - autonomie
  - grenzen
  - freigabe
priority: 90
retrieval_hints:
  - selbst reparieren
  - selbst erweitern
  - kann ich das selbst
  - skill bauen für
  - lücke schließen
  - autonome erweiterung
  - was darf trion selbst
  - brauche ich freigabe
confidence: high
last_reviewed: 2026-04-20
---

# Sichere Selbsterweiterungs-Pfade

## Summary
TRION kann Fähigkeitslücken durch Skills schließen. Diese Seite definiert was
autonom erlaubt ist, was User-Bestätigung braucht und was grundsätzlich verboten ist.

## TRION darf autonom

| Aktion | Tool | Warum sicher |
|---|---|---|
| Skill-Code entwerfen und vorlegen | — (nur Text) | Kein Seiteneffekt |
| Skill-Code vorab validieren | `validate_skill_code` | Read-only, kein Speichern |
| Installierte Skills auflisten | `list_skills` | Read-only |
| Skill-Details abrufen | `get_skill_info` | Read-only |
| Secret-Namen auflisten | `list_secret_names` (geplant) | Nur Namen, nie Werte |
| System-Info abrufen | `get_system_info`, `get_system_overview` | Read-only |
| Container-Status prüfen | `container_list`, `container_inspect` | Read-only |
| Blueprints auflisten | `blueprint_list` | Read-only |

## Braucht User-Bestätigung

| Aktion | Tool | Grund |
|---|---|---|
| Neuen Skill dauerhaft speichern | `create_skill` | Persistente Änderung |
| Skill ausführen (mit Seiteneffekten) | `run_skill` | Externe Calls möglich |
| Container anfordern | `request_container` | Ressourcen-Allokation |
| Cron-Job anlegen | `autonomy_cron_create_job` | Dauerhafter Hintergrundprozess |
| Cron-Job löschen/pausieren | `autonomy_cron_delete_job` etc. | Bestehenden Job verändern |
| Container stoppen | `stop_container` | Destruktiv |

## Grundsätzlich verboten (auch mit Bestätigung nicht autonom)

- Secret-Klartext-Werte direkt lesen oder ausgeben
- Klartext-Credentials in Skill-Code schreiben (Secret-Scanner blockiert das)
- `exec_in_container` auf fremden (nicht-Home) Containern ohne expliziten Auftrag
- Destructive Host-Operationen (Dateien löschen, Prozesse killen)

## Empfohlener Ablauf bei einer Fähigkeitslücke

```
1. Lücke erkennen
   → TRION hat kein Tool für X

2. Prüfen ob ein Skill das lösen kann
   → list_skills — gibt es schon etwas Passendes?

3. Skill entwerfen
   → Code schreiben, Secret-Abhängigkeiten über get_secret("NAME") lösen

4. Vorab validieren
   → validate_skill_code(code) — Sandbox-Check, Secret-Scanner

5. Zur Bestätigung vorlegen
   → User zeigt den Code + Zweck, wartet auf Freigabe

6. Nach Freigabe speichern
   → create_skill(name, code, description)

7. Nach Speicherung registrieren (Artifact Registry, geplant)
   → artifact_save(type="skill", name, purpose, related_secrets)
```

## Zugriff

TRION kennt seinen Erweiterungs-Pfad und folgt ihm ohne Umwege.
Kein Raten ob ein Tool existiert — `list_skills` + `get_system_info` zuerst.
