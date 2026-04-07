---
id: gaming-station-runtime
title: Gaming Station Runtime
scope: runtime
applies_to:
  blueprint_ids: [gaming-station]
  image_refs: [josh5/steam-headless:latest]
  container_tags: [gaming, headless-gui, steam, sunshine, supervisord]
tags:
  - gaming
  - headless-gui
  - x11
  - novnc
  - sunshine
  - steam
  - supervisord
priority: 95
retrieval_hints:
  - runtime
  - supervisord
  - display
  - novnc
  - sunshine ports
  - xorg
  - x11vnc
  - steam start
  - display variable
commands_available:
  - supervisorctl
  - ps
  - ss
  - netstat
  - curl
  - xrandr
  - xdpyinfo
  - xdotool
  - echo
confidence: high
last_reviewed: 2026-03-22
---

# Summary

Init ist `supervisord`. Kein systemd. Alle Dienste werden uber `supervisorctl` verwaltet.
Desktop lauft auf Xorg, Display `:55`. Steam und Sunshine starten nach dem Desktop.

## Environment

- **PID 1**: `supervisord`
- **Display**: `DISPLAY=:55`
- **Desktop-Session**: `xfce4-session`
- **VNC**: `x11vnc` lauscht auf Display `:55`
- **noVNC**: `websockify` bruckt VNC -> WebSocket auf intern `8083`
- **Sunshine**: WebUI auf `47990`, HTTP auf `47989`, RTSP auf `48010`, Game Stream UDP `48100-48110`
- **Package Manager**: `apt` (Debian-basiert)
- **GPU-Umgebungsvariablen**:
  - `NVIDIA_VISIBLE_DEVICES=all`
  - `NVIDIA_DRIVER_CAPABILITIES=all`

## Startsequenz (supervisord-Reihenfolge)

1. Xorg startet — Display `:55` wird verfugbar
2. x11vnc startet — VNC-Verbindung wird moglich
3. xfce4-session startet — Desktop wird sichtbar
4. websockify startet — noVNC wird erreichbar
5. Sunshine startet — Streaming-Dienst wird verfugbar
6. Steam startet (letzter Dienst, langste Startzeit)

## Wichtige Befehle

```bash
# Gesamtstatus aller Dienste
supervisorctl status

# Alle relevanten Prozesse prufbar
ps -ef | grep -E 'Xorg|x11vnc|xfce|sunshine|steam|websockify'

# Display verfugbar?
echo $DISPLAY
xrandr -display :55

# Ports
ss -ltnup

# noVNC erreichbar?
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8083/

# Sunshine WebUI erreichbar?
curl -s -o /dev/null -w "%{http_code}" https://127.0.0.1:47990/ -k

# Einzelnen Dienst neu starten (nur wenn sicher ausgefallen)
supervisorctl restart sunshine
supervisorctl restart x11vnc
```

## Logs

```bash
# Supervisor-Log
cat /var/log/supervisor/supervisord.log

# Dienstspezifische Logs (Pfade typisch)
ls /var/log/supervisor/
# oder
tail -n 50 /var/log/supervisor/sunshine-stdout.log
tail -n 50 /var/log/supervisor/steam-stdout.log
```

## Prefer

- Immer erst `supervisorctl status` — Gesamtbild vor Einzeldiagnose
- `ps -ef` wenn supervisorctl-Status unklar ist (Prozess kann laufen obwohl supervisord ihn als `STOPPED` zeigt)
- `ss -ltnup` fur Portstatus — verlasslicher als Prozessliste allein

## Avoid

- `systemctl` — nicht vorhanden
- `service <name> restart` — nicht zuverlassig, lieber `supervisorctl restart`
- Mehrfach `supervisorctl restart` ohne Zustandsprufung dazwischen
- Steam-Prozess killen ohne vorherige Prufung ob Update lauft
