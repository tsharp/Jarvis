---
id: headless-x11-novnc
title: Headless X11 and noVNC
scope: diagnostics
applies_to:
  container_tags: [headless-gui, x11, novnc]
tags:
  - headless-gui
  - x11
  - novnc
  - xorg
  - x11vnc
priority: 75
retrieval_hints:
  - black screen
  - novnc
  - xorg
  - x11vnc
  - display
commands_available:
  - ps
  - xrandr
  - xdpyinfo
  - curl
confidence: high
last_reviewed: 2026-03-22
---

# Summary

- For black screen issues, verify Xorg, the desktop session, and the VNC/web bridge separately.

## Prefer

- `ps -ef | grep -E 'Xorg|x11vnc|xfce|websockify' | grep -v grep`
- `echo $DISPLAY`
- `xrandr -display :55`
- `curl -I http://127.0.0.1:8083/`

## Avoid

- Assuming a reachable noVNC page means the desktop session is healthy.
- Restarting Xorg and x11vnc together as a first step.
