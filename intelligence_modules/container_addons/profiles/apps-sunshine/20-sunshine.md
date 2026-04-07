---
id: app-sunshine
title: Sunshine Service Diagnostics
scope: diagnostics
applies_to:
  container_tags: [sunshine]
tags:
  - sunshine
  - streaming
  - webui
priority: 72
retrieval_hints:
  - sunshine
  - stream
  - moonlight
  - web ui
  - encoder
commands_available:
  - ps
  - ss
  - curl
  - supervisorctl
confidence: high
last_reviewed: 2026-03-22
---

# Summary

- Sunshine problems should be checked at process, port, and UI levels.

## Prefer

- `ps -ef | grep sunshine | grep -v grep`
- `ss -ltnup | grep -E '47989|47990|48010'`
- `curl -sk -I https://127.0.0.1:47990/welcome`
- `supervisorctl tail sunshine stdout`

## Avoid

- blaming Sunshine before checking GPU/display prerequisites
- repeating restarts without log review
