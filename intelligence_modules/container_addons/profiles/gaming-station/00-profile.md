---
id: gaming-station-profile
title: Gaming Station Profile
scope: container_profile
applies_to:
  blueprint_ids: [gaming-station]
  image_refs: [josh5/steam-headless:latest]
  container_tags: [gaming, headless-gui, steam, sunshine]
tags:
  - gaming
  - headless-gui
  - steam
  - sunshine
priority: 100
retrieval_hints:
  - what container is this
  - runtime profile
  - installed services
  - gaming station
  - steam headless
commands_available: []
confidence: high
last_reviewed: 2026-03-22
---

# Summary

Headless Gaming-Container auf Basis von `josh5/steam-headless`.
Bietet einen vollstandigen Linux-Gaming-Desktop ohne physischen Monitor.
Zugang per noVNC (Browser) oder Sunshine/Moonlight (Low-Latency-Streaming).

## Environment

- **Blueprint**: `gaming-station`
- **Image**: `josh5/steam-headless:latest`
- **Init**: `supervisord` (PID 1) — kein systemd, kein OpenRC
- **Desktop**: XFCE4 auf Xorg
- **Display**: `:55` (`DISPLAY=:55`)
- **Zugang**:
  - noVNC (Browser-VNC): Port `47991` (intern `8083`)
  - Sunshine Web UI: Port `47990`
  - Sunshine HTTP: Port `47989`
  - Sunshine RTSP: Port `48010`
  - Game Stream UDP: Ports `48100–48110`
- **GPU**: NVIDIA, via `NVIDIA_VISIBLE_DEVICES=all` + `NVIDIA_DRIVER_CAPABILITIES=all`
- **Kernel-Anforderung**: `seccomp=unconfined` (sonst exit_code=32 in Flatpak-Init)

## Hauptdienste (via supervisord)

- `Xorg` — virtueller X11-Server
- `x11vnc` — VNC-Server fur noVNC
- `xfce4-session` — Desktop-Session
- `websockify` — noVNC-WebSocket-Bridge
- `sunshine` — Moonlight-Streaming-Dienst
- `steam` — Steam-Client (startet nach Desktop)

## Prefer

- Zustandsprufung immer mit `supervisorctl status` beginnen.
- Display-Fragen: `echo $DISPLAY` und `xrandr -display :55` verwenden.
- Porterreichbarkeit im Container: `ss -ltnup` oder `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8083/`

## Avoid

- `systemctl` — nicht vorhanden, gibt keine sinnvolle Fehlermeldung
- Annahme, dass noVNC-Black-Screen = Xorg-Absturz bedeutet
