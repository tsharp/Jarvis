---
id: gaming-station-diagnostics
title: Gaming Station Diagnostics
scope: diagnostics
applies_to:
  blueprint_ids: [gaming-station]
  image_refs: [josh5/steam-headless:latest]
  container_tags: [gaming, headless-gui, x11, novnc, sunshine, steam]
tags:
  - diagnostics
  - black-screen
  - novnc
  - xorg
  - sunshine
  - steam
priority: 90
retrieval_hints:
  - black screen
  - noVNC not working
  - sunshine crash
  - steam installer
  - display issues
  - container not ready
  - streaming not working
  - how to check
  - diagnose
commands_available:
  - supervisorctl
  - ps
  - xrandr
  - xdpyinfo
  - xdotool
  - curl
  - ss
  - tail
  - cat
confidence: high
last_reviewed: 2026-03-22
---

# Summary

Diagnose immer in drei Schichten:
1. Prozesse laufen? (supervisord-Ebene)
2. Display/X11 verfugbar? (Xorg-Ebene)
3. Dienst erreichbar? (Port/HTTP-Ebene)

Niemals mit Schicht 3 beginnen wenn Schicht 1 noch unbekannt ist.

## Schritt-fur-Schritt: Schnelldiagnose

```bash
# 1. Gesamtbild
supervisorctl status

# 2. Prozessdetails (falls supervisorctl unklar)
ps -ef | grep -E 'Xorg|x11vnc|xfce4|sunshine|steam|websockify|supervisord'

# 3. Display vorhanden?
echo $DISPLAY
xrandr -display :55 2>&1 | head -5

# 4. Alle relevanten Ports offen?
ss -ltnup | grep -E '8083|47989|47990|48010|4810[0-9]'

# 5. noVNC antwortet?
curl -s -o /dev/null -w "noVNC: %{http_code}\n" http://127.0.0.1:8083/

# 6. Sunshine WebUI antwortet?
curl -sk -o /dev/null -w "Sunshine WebUI: %{http_code}\n" https://127.0.0.1:47990/
```

## Diagnose: Black Screen in noVNC

Black Screen kann bedeuten:
- Xorg lauft, aber xfce4-session ist noch nicht gestartet (normal wahrend Boot)
- xfce4-session ist abgesturzt
- x11vnc hat die X11-Session verloren
- Auflsungskonflikt (xrandr)

```bash
# Ist Xorg da?
ps -ef | grep Xorg | grep -v grep

# Lauft xfce4-session?
ps -ef | grep xfce4-session | grep -v grep

# Lauft x11vnc?
ps -ef | grep x11vnc | grep -v grep

# x11vnc-Log prufbar
tail -n 30 /var/log/supervisor/x11vnc-stdout.log 2>/dev/null || \
  supervisorctl tail x11vnc stdout

# Aktuelle Auflosung
xrandr -display :55 | grep '*'
```

## Diagnose: Sunshine nicht erreichbar

```bash
# Sunshine-Prozess
ps -ef | grep sunshine | grep -v grep

# Port offen?
ss -ltnup | grep 47990

# Sunshine-Log
supervisorctl tail sunshine stdout
tail -n 50 /var/log/supervisor/sunshine-stdout.log 2>/dev/null

# Haufige Ursache: GPU nicht gefunden
# -> Pruf ob NVIDIA_VISIBLE_DEVICES gesetzt ist
echo $NVIDIA_VISIBLE_DEVICES
echo $NVIDIA_DRIVER_CAPABILITIES
```

## Diagnose: Steam lauft nicht / blockiert

```bash
# Prozessstatus
ps -ef | grep -i steam | grep -v grep
supervisorctl status steam 2>/dev/null

# Steam-Log
supervisorctl tail steam stdout
tail -n 50 /var/log/supervisor/steam-stdout.log 2>/dev/null

# Haufig: Steam-Installer wartet auf GUI-Interaktion
# -> Nicht automatisch weiterklicken — Zustand erst prufbar machen via xdotool
xdotool search --name "Steam" 2>/dev/null
```

## Diagnose: Container nach Start nicht bereit

```bash
# Reihenfolge der Prufung
supervisorctl status               # Alle Dienste geladen?
echo $DISPLAY                      # Display gesetzt?
xrandr -display :55 2>&1           # X11 antwortet?
ss -ltnup | grep 8083              # noVNC-Port offen?
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8083/  # noVNC antwortet?
```

## Verification

| Aktion                        | Verifikationsbefehl                                              |
|-------------------------------|------------------------------------------------------------------|
| Xorg lauft                    | `ps -ef \| grep Xorg \| grep -v grep`                          |
| Display verfugbar             | `xrandr -display :55 2>&1 \| grep -v error`                    |
| noVNC erreichbar              | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8083/` |
| Sunshine WebUI erreichbar     | `curl -sk -o /dev/null -w "%{http_code}" https://127.0.0.1:47990/` |
| x11vnc lauft                  | `ps -ef \| grep x11vnc \| grep -v grep`                        |
| Steam-Prozess aktiv           | `ps -ef \| grep steam \| grep -v grep`                         |

## Avoid

- Logs direkt mit `cat` lesen wenn sie sehr gro werden konnen — `tail -n 50` verwenden
- `xdotool` zur GUI-Steuerung einsetzen ohne vorher Fenster-Existenz zu prufen
- GPU-relevante Diagnose ohne Prufung von `NVIDIA_VISIBLE_DEVICES`
