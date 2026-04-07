---
id: container-query-classes
title: Container Query Classes
scope: inventory
tags:
  - taxonomy
  - inventory
  - state-binding
  - capability
  - blueprint
priority: 125
retrieval_hints:
  - welche container laufen
  - welche blueprints gibt es
  - welcher container ist aktiv
  - was kann dieser container
  - container status
  - container binding
confidence: high
last_reviewed: 2026-04-05
---

# Summary

Containerfragen muessen zuerst in eine Query-Klasse eingeordnet werden.
Erst danach darf Toolwahl und Antwortstruktur folgen.

## 1. Runtime Inventory

Beantwortet:
- welche Container laufen
- welche Container gestoppt sind
- welche Container an die aktuelle Session gebunden sind

Konzeptuelle Toolnamen:
- `list_running_containers`
- `list_stopped_containers`
- `list_attached_containers`
- `list_active_session_containers`
- `list_recently_used_containers`

Aktuelle autoritative Runtime-Basis:
- `container_list`

## 2. Blueprint Catalog

Beantwortet:
- welche Containergrundtypen existieren
- welche Blueprints startbar oder auswaehlbar sind

Konzeptuelle Toolnamen:
- `list_available_containers`
- `list_container_blueprints`
- `list_verified_blueprints`
- `list_installable_blueprints`
- `list_user_selectable_containers`

Aktuelle autoritative Runtime-Basis:
- `blueprint_list`

## 3. State / Binding

Beantwortet:
- welcher Container gerade aktiv ist
- woran dieser Turn oder diese Session gebunden ist
- wie der Runtime-Status eines bestimmten Containers aussieht

Konzeptuelle Toolnamen:
- `get_active_container`
- `get_active_container_context`
- `get_current_container_binding`
- `get_session_container_state`
- `get_container_runtime_status`

Aktuelle autoritative Runtime-Basis:
- Conversation-/Session-State
- `container_inspect`
- bei Bedarf `container_list`

## 4. Capability

Beantwortet:
- was ein bestimmter Container kann
- welches Tooling oder welche Runtime-Features dort vorhanden sind

Konzeptuelle Toolnamen:
- `get_container_capabilities`
- `describe_container_capabilities`
- `get_container_tooling`
- `get_container_runtime_features`
- `check_container_capability`

Aktuelle autoritative Runtime-Basis:
- `container_inspect`
- optional statischer Profilkontext aus `container_addons`
