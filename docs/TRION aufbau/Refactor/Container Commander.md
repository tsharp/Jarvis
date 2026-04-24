---
Tags: [TRION, Architecture, Container, Docker, MCP]
aliases: [Container Commander, engine.py, mcp_tools.py]
---

# 🐳 Container Commander

Der `container_commander/` ist das TRION-eigene Mini-Kubernetes/Docker-Compose System. Es ist dafür verantwortlich, isolierte Sandboxen für Code-Ausführung oder Sub-Services zu spawnen. Alles läuft über das PyPI-Package `docker`, mit dem sich TRION direkt an den Host-Daemon klinkt.

## 🏗️ 1. Kern-Architektur

Das Modul ist sehr mächtig und besitzt ein striktes Lifecycle-Management:

- **`engine.py`**: Der Kern. Er baut Images aus Blueprints, startet/stoppt Container, verwaltet das Netzwerk (`trion-sandbox`) und achtet penibel auf Ressourcen-Quotas (Memory/CPU).
- **`blueprint_store.py`**: Das Regelwerk. Definiert, *was* genau gestartet wird (Dockerfiles, Image-Tags, Mounts). 
- **`approval.py` & Trust-Gates**: Es gibt eingebaute "Human-in-the-Loop"-Sicherheitsnetze (`PendingApprovalError`). Das System verhindert (meistens), dass das LLM ungefragt Root-Rechte zieht oder gefährliche Hardware-Mounts erstellt.

## 🤖 2. Die KI-Schnittstelle (`mcp_tools.py`)

Das Commander-System wird dem TRION-LLM über das Model Context Protocol (MCP) als über **28 dedizierte Tools** zur Verfügung gestellt. 

Die KI kann hierdurch beängstigend viel alleine steuern:
- `request_container` / `stop_container`
- `exec_in_container` (Befehle in Sandboxen ausführen)
- `container_stats` / `optimize`
- `autonomy_cron_create_job` (TRION kann sich selbst Cronjobs programmieren, die autonom aufwachen und Container starten!)

---

## ⚠️ 3. Identify Technical Debt: Vermischung der Domains

Obwohl das System für sich genommen sauber orchestriert ist, gibt es in der Kapselung zwei massive "Smells" (Architektur-Probleme):

> [!warning] Architecture Smell 1: Hartkodierte Domänen (Gaming/Steam) in Core-Logik
> In der Core-API Datei `mcp_tools.py` gibt es Importe aus `mcp_tools_gaming.py` und direkte String-Checks für: `if blueprint_id in {"gaming-station", "steam-headless"}`. 
> Dass das Kern-Modul einer Docker-Orchestrierung plötzlich spezifische "Gaming-PCs" hardcodet abfängt, bricht das Open-Closed Principle komplett.

> [!warning] Architecture Smell 2: Layer Violation mit Orchestrator
> Wie wir bereits bei der Analyse des `Orchestrators` festgestellt haben, mischt sich der Orchestrator aktiv in die Hardware-Gates und Container-IDs ein. Eigentlich müsste der Orchestrator blind sein. Er sollte nur sagen: *"Container Commander, hier ist ein Intent. Mach du mal."* Aktuell kennen aber beide Ebenen (Orchestrator und Commander) die Intima der Containerverwaltung.

## 🛠️ 4. Refactoring-Plan

- **Spezialisierte Blueprints abstrahieren:** Die Sonderlogik für `gaming-station` darf nicht in `mcp_tools.py` gehardcodet sein. Das muss als sauberes Blueprint-Konfigurations-Objekt oder Plugin gekapselt werden.
- **Orchestrator entkoppeln:** Jegliches Wissen über Container-Hardware-Gates oder Limits muss aus `core/orchestrator.py` entfernt und exklusiv in den `container_commander` verschoben werden.
