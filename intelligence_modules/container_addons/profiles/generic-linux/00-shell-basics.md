---
id: generic-linux-shell-basics
title: Generic Linux Container Shell Basics
scope: diagnostics
applies_to:
  container_tags: [container-shell]
tags:
  - linux
  - shell
  - diagnostics
priority: 40
retrieval_hints:
  - basic diagnostics
  - process check
  - port check
  - log check
commands_available:
  - ps
  - ss
  - netstat
  - env
  - printenv
  - cat
  - tail
confidence: high
last_reviewed: 2026-03-22
---

# Summary

- Start with process, port, and log checks before making changes.

## Prefer

- `ps -ef`
- `ss -ltnup`
- `env | sort`
- `tail -n 50 <logfile>`

## Avoid

- Repeating the same command without checking state changes.
- Editing config files before reading current logs and runtime state.
