# Container Addon Spec

Dieses Format ist für `TRION shell` optimiert.

## Ziel

Ein Addon soll **nicht** komplette Doku ersetzen. Es soll nur die Informationen
liefern, die ein kleines Modell für sichere Shell-Entscheidungen braucht:

- worin läuft der Container
- welche Tools sind sinnvoll
- welche Kommandos sind typisch
- welche Fehlerbilder kommen häufig vor
- welche Kommandos sollte TRION vermeiden
- wie verifiziert man einen Schritt

Wichtig fuer den Container-Manager:

- Statisches Containerwissen und Live-Zustand bleiben getrennt.
- Ein Addon darf erklaeren, **was fuer ein Container-Typ** etwas ist.
- Ein Addon darf nicht als Wahrheitsquelle dafuer dienen, **ob** ein Container
  gerade laeuft, gestoppt ist oder an eine Session gebunden ist.
- Runtime-Inventar, aktuelle Bindung und Session-Zustand muessen aus Tools
  kommen.

## Dateiformat

Jede Addon-Datei ist eine Markdown-Datei mit YAML-Frontmatter.

Beispiel:

```md
---
id: gaming-station-runtime
title: Gaming Station Runtime
scope: container_profile
applies_to:
  blueprint_ids: [gaming-station]
  image_refs: [josh5/steam-headless]
tags:
  - gaming
  - headless-gui
  - steam
  - sunshine
  - supervisord
priority: 90
retrieval_hints:
  - black screen
  - novnc
  - sunshine crash
  - xorg
  - steam installer
commands_available:
  - supervisorctl
  - ps
  - xdotool
  - xrandr
  - ss
  - curl
confidence: high
last_reviewed: 2026-03-22
---

# Runtime

## Environment
- PID 1 is `supervisord`, not `systemd`.
- Desktop runs on Xorg with `DISPLAY=:55`.

## Prefer
- `supervisorctl status`
- `ps -ef`

## Avoid
- `systemctl`
```

## Frontmatter-Felder

Pflicht:

- `id`
- `title`
- `scope`
- `tags`
- `priority`

Optional aber empfohlen:

- `applies_to.blueprint_ids`
- `applies_to.image_refs`
- `applies_to.container_tags`
- `retrieval_hints`
- `commands_available`
- `confidence`
- `last_reviewed`

## Gültige `scope`-Werte

- `container_profile`
  Basiswissen zum Container-Typ
- `runtime`
  Init, Desktop, Ports, Prozessmodell, Package Manager
- `diagnostics`
  Diagnosepfade und Prüfbefehle
- `known_issues`
  typische Fehlerbilder und Workarounds
- `safety`
  Dinge, die TRION vermeiden oder doppelt prüfen soll
- `overview`
  statische Taxonomie oder Begriffsordnung fuer Containerfragen
- `inventory`
  Regeln fuer Laufzeitinventar vs. Blueprint-Katalog
- `state_binding`
  Regeln fuer aktiven Container, Session-Bindung und Statusfragen
- `capability_rules`
  Regeln fuer Capability-Fragen
- `answering_rules`
  Regeln fuer saubere Antworten ohne Vermischung von Wahrheitsquellen

## Inhaltliche Regeln

Ein Addon soll:
- kurze klare Sätze verwenden
- Befehle nur nennen, wenn sie realistisch im Container vorkommen
- Verifikation immer mitdenken
- read-only Diagnose von Änderungen trennen

Ein Addon soll nicht:
- lange Fließtexte enthalten
- generische Linux-Einführung wiederholen
- unsichere destructive commands als Default empfehlen
- sich auf Host-Wissen verlassen
- statische Containerbeschreibung als Live-Beweis verkaufen
- Blueprint-Wissen mit Runtime-Wahrheit vermischen
- "installierbar", "verfuegbar", "laufend" und "aktiv gebunden" synonym nutzen

## Empfohlene Sections

Nicht jede Datei braucht alle, aber diese Struktur ist ideal:

- `# Summary`
- `## Environment`
- `## Prefer`
- `## Avoid`
- `## Verification`
- `## Known Failure Patterns`
- `## Recovery Notes`

## Was Claude dafür von dir bekommen sollte

Für einen guten Addon-Entwurf braucht Claude möglichst diese Daten:

1. Container-Identität
- `blueprint_id`
- Image
- Zweck des Containers

2. Runtime
- PID 1 / Init-System
- Desktop- oder Headless-Stack
- Package Manager
- wichtige Prozesse / Supervisor-Namen

3. Erreichbarkeit
- veröffentlichte Ports
- welche Ports UI, Streaming, noVNC, VNC usw. sind

4. Tooling im Container
- welche Kommandos sicher vorhanden sind
- welche typischen Kommandos fehlen

5. Bekannte Probleme
- Crash-Muster
- Black-Screen-/Display-Probleme
- Healthcheck-Fallen

6. Sicherheitsregeln
- welche Kommandos TRION nicht blind nutzen soll
- welche Eingriffe manuell bestätigt werden sollen

## Gaming-Station: empfohlene Dateiaufteilung

Für `gaming-station` reichen am Anfang 4 Dateien:

- `00-profile.md`
  Was ist das für ein Container?
- `10-runtime.md`
  Init, X11, VNC, noVNC, Sunshine, Steam
- `20-diagnostics.md`
  sinnvolle Diagnosebefehle für Black Screen, Sunshine, Steam
- `30-known-issues.md`
  typische Fehlerbilder und Fallstricke

## Retrieval-Ziel

Später soll TRION **nicht** alle Addons komplett bekommen, sondern nur:
- die zum Container passenden Dateien
- daraus nur die wenigen relevanten Abschnitte

Deshalb:
- lieber mehrere kleine Dateien
- statt einer riesigen All-in-One-Datei
