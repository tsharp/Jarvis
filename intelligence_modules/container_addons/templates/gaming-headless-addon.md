---
id: gaming-headless-template
title: Gaming Headless Template
scope: runtime
applies_to:
  blueprint_ids: [gaming-station]
  image_refs: [josh5/steam-headless]
  container_tags: [gaming, headless-gui, steam, sunshine]
tags:
  - gaming
  - headless-gui
  - steam
  - sunshine
  - x11
  - novnc
  - supervisord
priority: 90
retrieval_hints:
  - black screen
  - novnc
  - sunshine
  - steam installer
  - xorg
  - x11vnc
commands_available:
  - supervisorctl
  - ps
  - ss
  - netstat
  - xdotool
  - xrandr
  - xdpyinfo
  - curl
confidence: high
last_reviewed: 2026-03-22
---

# Summary

- Headless Gaming-Container mit Xorg, noVNC, x11vnc, XFCE, Steam und Sunshine.

## Environment

- PID 1 ist typischerweise `supervisord`, nicht `systemd`.
- noVNC und VNC hängen an einer virtuellen X11-Session.
- Sunshine und Steam können später starten als Xorg/x11vnc.

## Prefer

- `supervisorctl status`
- `ps -ef | grep -E 'Xorg|x11vnc|xfce|sunshine|steam'`
- `ss -ltnup`
- `echo $DISPLAY`
- `xrandr -display :55`
- `curl -I http://127.0.0.1:<novnc-port>/`

## Avoid

- `systemctl ...`
- wiederholte GUI-Bestätigung ohne Zustandswechsel
- destruktive Steam-/Config-Änderungen ohne Verifikation

## Verification

- Nach GUI-/Desktop-Schritten prüfen:
  - läuft `Xorg`?
  - läuft `x11vnc`?
  - läuft `xfce4-session`?
  - antwortet noVNC?
- Nach Sunshine-Schritten prüfen:
  - Prozessstatus
  - Portstatus
  - WebUI-Erreichbarkeit

## Known Failure Patterns

- noVNC erreichbar, aber schwarzer Bildschirm trotz laufendem Xorg
- Sunshine startet, fällt aber später wieder aus
- Steam-Installer blockiert mit GUI-Dialog

## Recovery Notes

- Erst Runtime-/Display-Status prüfen
- dann GUI-/Session-Zustand prüfen
- erst danach spezifische App-Probleme debuggen
