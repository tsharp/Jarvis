---
id: app-steam-headless
title: Steam Headless Diagnostics
scope: diagnostics
applies_to:
  image_refs: [josh5/steam-headless]
  container_tags: [steam]
tags:
  - steam
  - steam-headless
  - installer
  - zenity
priority: 74
retrieval_hints:
  - steam
  - steam installer
  - zenity
  - update loop
commands_available:
  - ps
  - xdotool
  - tail
  - supervisorctl
confidence: high
last_reviewed: 2026-03-22
---

# Summary

- Steam may be slow to start and may block on a GUI installer or update prompt.

## Prefer

- `ps -ef | grep -i steam | grep -v grep`
- `xdotool search --name "Steam"`
- `supervisorctl tail steam stdout`

## Avoid

- blind repeated `xdotool` confirmation
- killing Steam during updates without checking logs
