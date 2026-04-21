---
id: system-topology-services
title: Service-Topologie im TRION-System
scope: topology
tags:
  - services
  - ports
  - docker
  - urls
  - netzwerk
priority: 85
retrieval_hints:
  - welche services
  - service map
  - auf welchem port
  - interne url
  - docker netz
  - erreichbar
  - container name
  - läuft auf
confidence: high
last_reviewed: 2026-04-21
---

## Invarianten

- Diese Datei beschreibt statische Service-Topologie.
- Diese Datei beschreibt keine Live-Verfügbarkeit.
- Service-Existenz != Service-läuft.
- Interne Kommunikation erfolgt per Docker-DNS über `container_name`.
- Interne URL-Form: `http://<container_name>:<internal_port>`

## Service-Map

| service | interne_url | host_port | zweck | zugriffsmodus |
|---|---|---:|---|---|
| lobechat-adapter | `http://lobechat-adapter:8100` | 8100 | Frontend-Adapter | indirekt |
| jarvis-webui | `http://jarvis-webui:80` | 8400 | Web-UI / nginx | indirekt |
| trion-runtime | `http://trion-runtime:8401` | 8401 | Haupt-Orchestrator | direkt |
| jarvis-admin-api | `http://jarvis-admin-api:8200` | 8200 | Admin-API | direkt |
| mcp-sql-memory | `http://mcp-sql-memory:8081` | 8082 | SQL Memory + Secret-Vault | indirekt |
| cim-server | `http://cim-server:8086` | 8086 | CIM / Embedding-Server | direkt |
| sequential-thinking | `http://sequential-thinking:8085` | 8085 | Sequential Thinking MCP | indirekt |
| document-processor | `http://document-processor:8087` | 8087 | Dokument-Verarbeitung | direkt |
| validator-service | `http://validator-service:8000` | 8300 | Code-Validator | direkt |
| trion-skill-server | `http://trion-skill-server:8088` | 8088 | Skill-Server (MCP) | indirekt |
| tool-executor | `http://tool-executor:8000` | 8000 | Skill-Runner / Skill-Persistenz | direkt |
| storage-broker | `http://storage-broker:8089` | 8089 | Storage-Broker MCP | indirekt |
| digest-worker | kein HTTP-Port | - | interner Worker | kein_direktzugriff |
| storage-host-helper | kein HTTP-Port | - | Host-Storage-Helfer | kein_direktzugriff |

## Netzwerk-Regeln

- Interne Service-zu-Service-Kommunikation nutzt Container-Namen.
- Externe Host-Ports sind kein bevorzugter interner Pfad.
- Externe Erreichbarkeit läuft über nginx/Proxy.
- Resolve-sensitive Endpoints dürfen nicht als öffentlich angenommen werden.
- Interne Topologie ist Wissen. Live-Erreichbarkeit muss via Tools geprüft werden.

## Direkt ansprechbare Services

- `trion-runtime`
- `jarvis-admin-api`
- `tool-executor`
- `validator-service`
- `document-processor`
- `cim-server`

## Indirekte Services

Primär über MCP- oder Bridging-Schicht verwenden:

- `mcp-sql-memory`
- `sequential-thinking`
- `trion-skill-server`
- `storage-broker`

## Nicht als normale Zielsysteme behandeln

- `jarvis-webui`
- `digest-worker`
- `storage-host-helper`

## Zugriff

- Für Live-Zustand zuerst Tools nutzen: `get_system_info`, `get_system_overview`, Container-Tools, Runtime-/Admin-Status.
- Interne URLs nur als statische Zieladressen verwenden, nicht als Verfügbarkeitsbeweis.
- Wenn ein MCP-/Native-Tool existiert, Tool-Pfad gegenüber rohem Direktcall bevorzugen.

## Grenzen

- Diese Datei sagt nicht, ob ein Service läuft.
- Diese Datei sagt nicht, ob ein Port erreichbar ist.
- Diese Datei sagt nicht, ob ein Tool aktuell registriert ist.
- Diese Datei ersetzt keinen Health-Check.
