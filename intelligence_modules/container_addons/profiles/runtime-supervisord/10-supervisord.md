---
id: runtime-supervisord
title: Supervisord Runtime
scope: runtime
applies_to:
  container_tags: [supervisord]
tags:
  - supervisord
  - supervisorctl
  - init
priority: 70
retrieval_hints:
  - supervisor
  - supervisord
  - service status
  - init system
commands_available:
  - supervisorctl
  - ps
  - tail
confidence: high
last_reviewed: 2026-03-22
---

# Summary

- PID 1 is `supervisord`. Do not assume `systemd`.

## Prefer

- `supervisorctl status`
- `supervisorctl tail <service> stdout`
- `supervisorctl restart <service>`

## Avoid

- `systemctl`
- `service <name> restart`
- restarting multiple services at once without verification

## Verification

- compare `supervisorctl status`
- confirm the real process via `ps -ef`
- confirm the expected port or log output
