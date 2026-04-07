---
id: container-taxonomy-overview
title: Container Taxonomy Overview
scope: overview
tags:
  - taxonomy
  - container-manager
  - inventory
  - blueprint
  - capability
priority: 120
retrieval_hints:
  - welche container
  - container manager
  - available containers
  - running containers
  - active container
  - container capabilities
  - blueprint list
  - runtime inventory
confidence: high
last_reviewed: 2026-04-05
---

# Summary

Diese Taxonomie trennt Containerfragen in verschiedene Wahrheitsklassen.
Sie ist statisch. Sie erklaert Begriffe und Antwortregeln, aber sie beweist
nicht den aktuellen Live-Zustand.

## Kerntrennung

- Blueprint-/Katalogwissen beantwortet: Was existiert grundsaetzlich oder ist startbar?
- Runtime-Inventar beantwortet: Was laeuft oder ist installiert?
- Session-/Binding-Zustand beantwortet: Woran ist dieser Turn gerade gebunden?
- Capability-Wissen beantwortet: Was kann ein bestimmter Container?

## Wahrheitsquellen

- Statische Erklaerung: `intelligence_modules/container_addons/taxonomy/*`
- Container-/Blueprint-Profile: `intelligence_modules/container_addons/profiles/*`
- Laufzeitinventar: Runtime-Tools wie `container_list`
- Blueprint-Katalog: Runtime-Tools wie `blueprint_list`
- Aktiver Container: Session-/Conversation-State plus `container_inspect`

## Nicht vermischen

- `list_container_blueprints` ist nicht dasselbe wie `list_running_containers`.
- `installierbar` ist nicht dasselbe wie `laeuft`.
- `aktiv` ist nicht dasselbe wie `in dieser Session gebunden`.
- Statische Profiltexte sind kein Live-Beweis.
