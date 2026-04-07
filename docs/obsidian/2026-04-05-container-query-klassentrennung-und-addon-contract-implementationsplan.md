# Container-Query-Klassentrennung und Addon-Contract - Implementationsplan

Erstellt am: 2026-04-05
Zuletzt aktualisiert: 2026-04-07
Status: **In Umsetzung**
Bezieht sich auf:

- [[2026-04-01-control-authority-drift-container-clarification-implementationsplan]] - frueherer Container-Plan fuer autoritative Tool-/Control-Korrekturen
- [[2026-04-01-container-capability-followup-grounding-fix]] - aktiver Container als eigener Capability-Pfad
- [[2026-03-31-container-session-state-konsolidierung]] - vorhandene Container-Conversation-State-Wahrheit
- [[2026-04-01-trion-home-container-addons]] - bestehende Container-Addon-Basis
- [[2026-03-22-container-commander-trion/04-Container-Addons]] - Zielbild fuer Blueprint-/Containerwissen
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]] - Thinking nur als Rohsignal, nicht als Autoritaet
- [[2026-03-31-control-layer-audit]] - Control als bindende Policy-Autoritaet

---

## Update 2026-04-07 - Home-Start-Reuse und Inventory-Grounding live nachgezogen

Der noch offene Folgestrang rund um `TRION Home` und der bereits als
"praktisch nachgezogen" markierte Inventory-Contract haben im echten
Live-Pfad noch zwei konkrete Fehler gezeigt, die jetzt behoben und lokal
verifiziert sind.

Neu gefixt:

- `home_start` hat einen vorhandenen `trion-home`-Container bisher auch dann
  direkt wiederverwendet, wenn er nur `stopped` war; dadurch konnte der
  sichtbare Tool-Output wie ein erfolgreicher Start aussehen, obwohl im
  Backend kein laufender Home-Container vorhanden war
- der Home-Helper startet gestoppte `trion-home`-Container jetzt explizit neu
  und initialisiert danach wieder das Home-Verzeichnis:
  [container_commander/mcp_tools_home.py](<repo-root>/container_commander/mcp_tools_home.py)
- der Workspace-/Chat-Eventbau behandelt `home_start` jetzt wie
  `request_container`, damit `container_started` auch fuer den Home-Fast-Path
  gebaut wird:
  [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- im `container_inventory`-Pfad wurden korrekte `container_list`-Daten im
  Grounding teilweise wieder verloren, weil die strukturierte Evidence
  (`containers`) bei der Normalisierung nicht in `structured` erhalten blieb
- die Grounding-Evidence konserviert fuer `container_list` und
  `blueprint_list` jetzt die strukturierten Zeilen explizit:
  [core/orchestrator_grounding_evidence_utils.py](<repo-root>/core/orchestrator_grounding_evidence_utils.py)

Lokal live verifiziert:

- direkter `home_start`-Call liefert nach Restart wieder `status=running`
- `list_containers()` und `container_list` zeigen `trion-home` wieder als
  laufend
- sichtbarer Prompt:
  - `starte bitte den TRION Home Workspace`
    -> Home-Container bleibt im Backend wirklich `running`
  - `welche container hast du, und welcher Container sind an und welche sind aus?`
    -> `Laufende Container: trion-home.`
    -> `Gestoppte Container: runtime-hardware, filestash.`
  - `welcher Container ist gerade aktiv?`
    -> in einer frisch gebundenen Conversation wird `container_state_binding`
       jetzt bei Drift sauber auf Binding-/Runtime-Fallback zurueckgezogen
    -> nach `jarvis-admin-api`-Restart ohne neu gesetzten Conversation-State
       bleibt die sichtbare Antwort bewusst konservativ:
       `Aktiver Container: nicht verifiziert.`
       `Binding/Status: Laufende TRION-managed Container: trion-home.`

Verifiziert:

- `pytest -q tests/unit/test_mcp_tools_home.py` -> `1 passed`
- `pytest -q tests/unit/test_orchestrator_runtime_safeguards.py -k 'home_start or container_event_content'`
  -> `3 passed`
- `pytest -q tests/unit/test_orchestrator_grounding_evidence_utils.py`
  -> `5 passed`
- `pytest -q tests/unit/test_output_grounding.py -k 'container_state_binding_postcheck'`
  -> `2 passed`
- gezielte neue Regressionen in
  [tests/unit/test_mcp_tools_home.py](<repo-root>/tests/unit/test_mcp_tools_home.py),
  [tests/unit/test_orchestrator_runtime_safeguards.py](<repo-root>/tests/unit/test_orchestrator_runtime_safeguards.py)
  und
  [tests/unit/test_orchestrator_grounding_evidence_utils.py](<repo-root>/tests/unit/test_orchestrator_grounding_evidence_utils.py),
  [tests/unit/test_output_grounding.py](<repo-root>/tests/unit/test_output_grounding.py)

Praezisierung zum Reststand:

- `container_inventory`, `container_blueprint_catalog` und
  `container_state_binding` sind damit nicht nur im Contract, sondern auch im
  sichtbaren Fallback-/Grounding-Pfad lokal belastbar verifiziert
- `ConversationContainerState` ist jetzt auch ueber
  `jarvis-admin-api`-Restarts hinweg persistent:
  [core/conversation_container_state.py](<repo-root>/core/conversation_container_state.py)
  schreibt nach `/app/data/conversation_container_state.json` und laedt diesen
  Zustand beim Store-Init wieder ein
- der Commander-Seeding-Pfad schreibt Bindings jetzt kanonisch mit Docker-
  Voll-ID statt mit einer eventuell kurzen Route-ID:
  [adapters/admin-api/commander_api/containers.py](<repo-root>/adapters/admin-api/commander_api/containers.py)
- live verifiziert ueber echten Commander-Seed
  `POST /api/commander/containers/<short-id>/trion-shell/start`
  plus `docker compose restart jarvis-admin-api`:
  dieselbe Conversation-Bindung wird danach im frischen Prozess wieder
  geladen und behaelt die kanonische Voll-ID
- neue Regressionen dafuer in
  [tests/unit/test_conversation_container_state.py](<repo-root>/tests/unit/test_conversation_container_state.py)
  (`27 passed`)
- offener Hauptrest bleibt jetzt wieder der getrennte
  `container_request`-/Home-Start-/Routing-Folgepfad jenseits dieses
  konkreten Reuse-/Binding-Fixes
- der breitere End-to-End-Recheck ueber komplette Runtime-Toolwrapper bleibt
  als naechster sauberer Schritt weiterhin sinnvoll

---

## Update 2026-04-06 - Resolver-Kopplung, Output-Contract und Live-Recheck nachgezogen

Der zweite Codeschnitt fuer den Container-Query-Contract ist jetzt ebenfalls im
Code verankert und mit lokalem Live-Recheck gegen den sichtbaren Output
nachgeprueft.

Neu umgesetzt:

- `load_container_addon_context(..., query_class=...)` ist jetzt explizit an
  die Query-Klasse gekoppelt
- Addon-Selektion ist damit nicht mehr nur textheuristisch:
  - `container_inventory`
  - `container_blueprint_catalog`
  - `container_state_binding`
  - `container_request`
    -> priorisieren statische `taxonomy/`
  - `active_container_capability`
    -> darf weiter `taxonomy/` plus `profiles/` nutzen
- der Output-Layer liest `_container_query_policy` jetzt aktiv und erzwingt
  sichtbare Antwortcontracts fuer:
  - `container_inventory`
  - `container_blueprint_catalog`
  - `container_state_binding`
- der Postcheck puffert diese Container-Contracts jetzt wie beim
  Skill-Catalog gepuffert und repariert sichtbare Modell-Drift mit einem
  container-spezifischen Safe-Fallback statt mit generischem
  Evidence-Summary-Text

Lokal live verifiziert:

- Runtime-Inventar ueber echten lokalen Docker-Bestand (`docker ps -a`)
- Blueprint-Katalog ueber den lokalen Store unter
  [memory/blueprints.db](<repo-root>/memory/blueprints.db)
- sichtbarer Output ueber lokales Ollama mit `ministral-3:3b`

Beobachteter wichtiger Befund:

- das kleine lokale Outputmodell driftet bei diesen Containerfragen im ersten
  Rohentwurf weiter gelegentlich:
  - Inventar -> spekulative Exit-/Zeit-Deutung
  - Blueprint -> unberechtigte Runtime-Aussagen
  - Binding -> ungefragte Action-/Diagnose-Spekulation
- die sichtbare Endantwort bleibt jetzt trotzdem contract-konform, weil der
  container-spezifische Postcheck diese Drifts in ein sauberes
  Inventory-/Blueprint-/Binding-Geruest zurueckzieht

Verifiziert:

- `pytest -q tests/unit/test_container_addons_loader_contract.py` -> `6 passed`
- `pytest -q tests/unit/test_output_tool_injection.py` -> `12 passed`
- `pytest -q tests/unit/test_output_grounding.py` -> `42 passed`
- gezielte Container-Postcheck-Regressionen in
  [tests/unit/test_output_grounding.py](<repo-root>/tests/unit/test_output_grounding.py)
  -> `3 passed`
- lokaler Output-Live-Recheck fuer:
  - `Welche Container hast du gerade zur Verfuegung?`
  - `Welche Blueprints gibt es?`
  - `Welcher Container ist gerade aktiv?`

Aktueller Rest:

- `container_request`-/Home-Start-/Routing-Drift bleibt eigener Folgestrang
  und ist **nicht** durch diesen Contract-Fix erledigt
- breiterer echter End-to-End-Recheck ueber komplette Tool-Wrapper bleibt
  weiterhin sinnvoll; lokal waren dafuer hier u. a. `docker`-Python-Modul und
  `/app/data`-Storepfad nicht direkt nutzbar

---

## Update 2026-04-05 - Erster Implementationsschnitt umgesetzt

Der erste Codeschnitt fuer die Container-Query-Klassentrennung ist jetzt im
Codepfad verankert.

Stand:

- `coerce_thinking_plan_schema(...)` kanonisiert Containerfragen jetzt auf:
  - `container_inventory`
  - `container_blueprint_catalog`
  - `container_state_binding`
  - `container_request`
  - `active_container_capability`
- der Orchestrator materialisiert jetzt frueh einen
  `_container_query_policy`-Block auf `verified_plan`
- die finale Toolwahl wird fuer diese Klassen jetzt deterministisch
  ueberschrieben:
  - `container_inventory` -> `container_list`
  - `container_blueprint_catalog` -> `blueprint_list`
  - `container_state_binding` -> `container_inspect` oder `container_list`
  - `container_request` -> `request_container`
  - `active_container_capability` -> `container_inspect`
- Keyword-Fallbacks wie
  `welche Container` -> `blueprint_list`
  sind auf Runtime-Inventar ausgerichtet
- `container_addons` lesen jetzt neben `profiles/` auch `taxonomy/` und
  tragen damit statische Begriffsregeln getrennt von Live-Wahrheit

Neu angelegt:

- [intelligence_modules/container_addons/taxonomy/00-overview.md](<repo-root>/intelligence_modules/container_addons/taxonomy/00-overview.md)
- [intelligence_modules/container_addons/taxonomy/10-static-containers.md](<repo-root>/intelligence_modules/container_addons/taxonomy/10-static-containers.md)
- [intelligence_modules/container_addons/taxonomy/20-query-classes.md](<repo-root>/intelligence_modules/container_addons/taxonomy/20-query-classes.md)
- [intelligence_modules/container_addons/taxonomy/30-answering-rules.md](<repo-root>/intelligence_modules/container_addons/taxonomy/30-answering-rules.md)

Verifiziert:

- `pytest -q tests/unit/test_container_addons_loader_contract.py` -> `4 passed`
- `pytest -q tests/unit/test_orchestrator_plan_schema_utils.py` -> `12 passed`
- `pytest -q tests/unit/test_control_contract_flow.py` -> `12 passed`
- `pytest -q tests/unit/test_thinking_layer_prompt.py` -> `14 passed`
- gezielte neue Container-Faelle in
  [tests/unit/test_orchestrator_runtime_safeguards.py](<repo-root>/tests/unit/test_orchestrator_runtime_safeguards.py)
  -> `6 passed`

Offen bleibt:

- `container_request`-/Home-Start-/Routing-Drift als eigener Folgepfad
- breiteren End-to-End-Recheck spaeter noch ueber vollstaendige Runtime-Toolpfade fahren

Wichtig:

- die komplette Datei
  [tests/unit/test_orchestrator_runtime_safeguards.py](<repo-root>/tests/unit/test_orchestrator_runtime_safeguards.py)
  haengt in diesem Workspace nach einem Teil der Suite ohne weitere Ausgabe
  und wurde deshalb fuer die neuen Container-Faelle gezielt statt vollstaendig
  verifiziert

---

## Anlass

Der aktuelle Container-Live-Befund zeigt einen semantischen Mischfehler:

- User fragt:
  - `welche Container hast du zur Verfuegung?`
- Thinking/Trace landet bei:
  - `resolution_strategy = active_container_capability`
  - `strategy_hints = ["container_list"]`
  - `suggested_tools = ["request_container"]`
- die sichtbare Antwort beschreibt dann nur einen kleinen Blueprint-/Sandbox-
  Ausschnitt statt den tatsaechlichen Container-Bestand

Der reale lokale Docker-Bestand ist aber deutlich breiter, u. a.:

- `trion-runtime` laeuft
- `trion-home` ist installiert, aber gestoppt
- `runtime-hardware` ist installiert, aber gestoppt
- `filestash` ist installiert, aber gestoppt

Damit ist der Kernfehler nicht nur ein schlechter Antworttext, sondern eine
fehlende Trennung zwischen mehreren Bedeutungen von "Container".

---

## Kurzbefund

Heute werden mindestens fuenf semantisch verschiedene Fragetypen noch nicht
hart genug getrennt:

1. Laufender/installierter Container-Bestand
2. Blueprint-/Container-Katalog
3. Aktiver Container / Session-Bindung
4. Aktiver Container und seine Faehigkeiten
5. Container anfordern / starten / deployen

Aktuelle Drift-Symptome:

- Inventarfragen koennen auf `request_container` laufen
- "welche Container" wird im Fallback derzeit eher wie
  `blueprint_list` behandelt als wie Runtime-Inventar
- `active_container_capability` kann zu breit gezogen werden, obwohl der User
  gar keinen deiktischen aktiven Container meint
- `container_addons` existieren bereits sinnvoll fuer Capability-/Blueprint-
  Wissen, kommen aber zu spaet, um falsches Routing zu korrigieren

Architekturproblem:

- Routing-/Toolwahl und semantische Begriffsordnung werden noch nicht sauber
  geschichtet
- dadurch muss der Output spaeter Dinge "retten", die frueher bereits falsch
  eingeordnet wurden

---

## Zielbild

Containerfragen sollen kuenftig erst deterministisch in Query-Klassen
eingeordnet werden. Erst danach wird bei Bedarf semantischer Addon-Kontext
geladen.

Reihenfolge:

1. Thinking liefert nur Rohsignale
2. Orchestrator/Plan-Schema kanonisiert auf eine Container-Query-Klasse
3. Control friert daraus einen kleinen Container-Contract ein
4. Resolver laedt daraus die autoritativen Tools
5. `container_addons` liefern nur noch Antwortsemantik und Begriffsregeln

Nicht Ziel:

- `container_addons` als Ersatz fuer Tool-Routing zu missbrauchen
- Blueprint-Wissen als Runtime-Wahrheit zu behandeln
- Container-Inventar komplett aus Prompting statt aus Tool-Snapshots abzuleiten

---

## Query-Klassen

Die naechste saubere Trennung fuer Containerfragen ist:

### 1. `container_inventory`

Fragetyp:

- `welche Container hast du`
- `welche Container laufen`
- `welche Container sind installiert`
- `welche Trion-Container gibt es gerade`

Autoritative Tools:

- `container_list`

Antwortsemantik:

- laufend vs. gestoppt/installiert sauber trennen
- optional TRION-Fokus plus Restbestand
- keine Blueprint-Katalog-Antwort

### 2. `container_blueprint_catalog`

Fragetyp:

- `welche Blueprints gibt es`
- `welche Container kann ich starten`
- `welche Sandboxes stehen zur Auswahl`

Autoritative Tools:

- `blueprint_list`

Antwortsemantik:

- verfuegbare Typen/Blueprints
- keine Behauptung ueber aktuell laufende Container

### 3. `container_state_binding`

Fragetyp:

- `welcher Container ist gerade aktiv`
- `auf welchen Container ist dieser Turn gebunden`
- `wie ist der Runtime-Status dieses Containers`

Autoritative Tools:

- `container_inspect`
- bei fehlendem aktivem Ziel optional `container_list`

Antwortsemantik:

- aktiver Container, Binding oder Session-Zustand
- keine Blueprint-Katalog-Antwort
- keine reine Capability-Liste als Hauptantwort

### 4. `active_container_capability`

Fragetyp:

- `was kannst du in diesem Container tun`
- `was ist hier installiert`
- `wofuer ist dieser Container da`

Autoritative Tools:

- `container_inspect`
- optional spaeter `container_addons` als semantischer Kontext

Antwortsemantik:

- konkreter aktiver Container
- Blueprint-/Image-/Addon-gebundene Faehigkeiten
- keine Inventarliste

### 5. `container_request`

Fragetyp:

- `starte einen Container`
- `deploye ...`
- `ich brauche eine Python-Sandbox`

Autoritative Tools:

- `request_container`

Antwortsemantik:

- Start-/Clarification-/Approval-Pfad
- keine Inventar- oder Blueprint-Liste als Hauptantwort

---

## Kernregel

`container_addons` werden kuenftig nur noch fuer semantische Einordnung,
Begriffsregeln und Antwortmodus geladen.

Sie entscheiden **nicht**:

- welche Query-Klasse vorliegt
- welche Runtime-Tools autoritativ sind
- welche Inventarwahrheit gilt

Die Autoritaet bleibt:

- `container_list` fuer Runtime-/Installationsinventar
- `blueprint_list` fuer Blueprint-Katalog
- `container_inspect` plus Session-State fuer aktiven Container / Binding und
  aktive Capability-Fragen
- `request_container` fuer Start-/Deploy-Interaktion

---

## Zielarchitektur in Kurzform

1. `coerce_thinking_plan_schema(...)` oder ein naher Container-Normalizer setzt
   die kanonische Container-Query-Klasse
2. ein frueher `_container_query_policy`-Block wird auf `verified_plan`
   materialisiert
3. final erlaubte Tools werden aus dieser Klasse abgeleitet, nicht aus freien
   Modellvorschlaegen
4. ein spaeter Resolver laedt optional passendes `container_addons`-Wissen
5. Output rendert innerhalb des Contracts und trennt Runtime-Inventar,
   Blueprints, Binding und aktiven Container sichtbar

---

## Implementationsbloecke

### Block 1 - Container-Query-Klassen frueh kanonisieren

Status:

- **Umgesetzt**

Ziel:

- Containerfragen sollen nicht mehr zwischen Inventar, Blueprint, aktivem
  Container und Request verschwimmen

Aenderungen:

- [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
  - neue kanonische Container-Strategien oder Container-Substrategie einfuehren
  - Thinking-Rohsignale auf eine kleine Allowlist reduzieren
  - deiktische aktive Container-Queries enger von allgemeinen Inventarfragen
    trennen
- optional:
  - `_raw_strategy_hints` / `_raw_container_hints` fuer Debug behalten

Regelbeispiele:

- `welche container`, `welche laufen`, `welche sind installiert`
  -> `container_inventory`
- `welche blueprints`, `welche sandboxes`, `welche container kann ich starten`
  -> `container_blueprint_catalog`
- `welcher container ist aktiv`, `auf welchen container ist dieser turn gebunden`
  -> `container_state_binding`
- `diesem container`, `this container`, `current container` plus Capability-
  Marker -> `active_container_capability`
- `starte`, `deploye`, `brauche einen container`
  -> `container_request`

Tests:

- neuer Testpfad in
  [tests/unit/test_orchestrator_plan_schema_utils.py](<repo-root>/tests/unit/test_orchestrator_plan_schema_utils.py)
- Container-Inventar-Prompt darf nicht mehr auf
  `active_container_capability` oder `request_container` fallen

Akzeptanzkriterium:

- `welche Container hast du zur Verfuegung?`
  endet kanonisch bei `container_inventory`

### Block 2 - Fruehen Container-Policy-Contract materialisieren

Status:

- **Umgesetzt** als erster kleiner Contract, noch ohne finalen Output-Section-Block

Ziel:

- spaetere Layer sollen nicht mehr frei zwischen Blueprint, Inventory und
  Request umdeuten

Vorschlag fuer neuen Block auf `verified_plan`:

```json
{
  "_container_query_policy": {
    "query_class": "container_inventory",
    "required_tools": ["container_list"],
    "truth_mode": "runtime_inventory"
  }
}
```

Aenderungen:

- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
  - Policy-Materialisierung analog zum Skill-Catalog-Prinzip
- Trace soll mindestens sichtbar machen:
  - `query_class`
  - `required_tools`
  - `truth_mode`

Tests:

- neuer Contract-Test in
  [tests/unit/test_control_contract_flow.py](<repo-root>/tests/unit/test_control_contract_flow.py)
  oder dedizierter Container-Contract-Test

Akzeptanzkriterium:

- Inventarfragen tragen frueh einen sichtbaren Read-only-Contract

### Block 3 - Toolwahl strikt aus Query-Klasse ableiten

Status:

- **Umgesetzt**

Ziel:

- freie Modellvorschlaege duerfen fuer Containerfragen nicht mehr die
  Runtime-Wahrheit ueberschreiben

Aenderungen:

- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
  - Container-Domain-Route auf Query-Klasse umstellen
  - Toolwahl fuer Containerfragen hart mappen:
    - `container_inventory` -> `container_list`
    - `container_blueprint_catalog` -> `blueprint_list`
    - `container_state_binding` -> `container_inspect` oder `container_list`
    - `active_container_capability` -> `container_inspect`
    - `container_request` -> `request_container`
- Fallback-Keyword-Pfade wie `welche container -> blueprint_list`
  auf das neue Zielbild angleichen

Tests:

- neue Regressionen in
  [tests/unit/test_orchestrator_domain_routing_policy.py](<repo-root>/tests/unit/test_orchestrator_domain_routing_policy.py)
- Inventarfrage darf nicht `request_container` oder nur `blueprint_list`
  bekommen

Akzeptanzkriterium:

- der finale Toolsatz ist fuer Containerfragen policy-konsistent

### Block 4 - Container-Addons als semantischen Resolver, nicht als Router nutzen

Status:

- **Umgesetzt** als explizite `query_class`-Kopplung im Loader

Ziel:

- `container_addons` sollen flexibel erklaeren, aber keine Routing-Autoritaet
  haben

Aenderungen:

- Resolver fuer Containerkontext nur nach bereits entschiedener Query-Klasse
  laden
- moegliche Addon-Module:
  - Inventar-/Antwortregeln fuer `container_inventory`
  - Blueprint-Begriffsregeln fuer `container_blueprint_catalog`
  - State-/Binding-Regeln fuer `container_state_binding`
  - bestehender aktiver Capability-Kontext fuer `active_container_capability`
- [intelligence_modules/container_addons/loader.py](<repo-root>/intelligence_modules/container_addons/loader.py)
  - Addon-Auswahl an Query-Klasse koppelbar machen

Aktueller Stand:

- statische Taxonomie-Dateien unter
  [intelligence_modules/container_addons/taxonomy](<repo-root>/intelligence_modules/container_addons/taxonomy)
  sind angelegt
- Loader liest `taxonomy/` und `profiles/`
- die harte Query-Klassen-Autoritaet liegt jetzt im Code, nicht in den Addons
- die Addon-Auswahl ist jetzt explizit an `query_class` gekoppelt:
  - Inventory-/Blueprint-/Binding-/Request-Klassen priorisieren statische
    Taxonomie
  - `active_container_capability` darf weiter Profilwissen plus Taxonomie
    laden

Wichtig:

- Addons duerfen Antworten strukturieren
- Addons duerfen Tools nicht ersetzen

Tests:

- Prompt-/Flow-Tests fuer Container-Inventory-Antwortmodus
- aktive Capability-Tests duerfen nicht regressieren

Akzeptanzkriterium:

- Inventarantworten bleiben an `container_list` geerdet, selbst wenn Addons
  semantischen Zusatzkontext liefern

### Block 5 - Sichtbaren Output fuer Container-Inventar strukturieren

Status:

- **Umgesetzt** als erster sichtbarer Output-Contract mit gepuffertem
  Postcheck-Safe-Fallback

Ziel:

- Container-Inventar und Blueprint-Katalog sollen fuer User sichtbar getrennt
  bleiben

Vorschlag fuer Antwortgeruest bei `container_inventory`:

- `Laufende Container`
- `Gestoppte Container`
- `Einordnung`

Optional:

- `Verfuegbare Blueprints` nur dann, wenn die Frage explizit beide Ebenen meint
  und dafuer auch `blueprint_list` ausgefuehrt wurde

Aenderungen:

- [core/layers/output.py](<repo-root>/core/layers/output.py)
  - eigener sichtbarer Container-Answer-Contract fuer:
    - Inventory
    - Blueprint-Katalog
    - Binding
  - keine Vermischung von Blueprint-Katalog und Runtime-Inventar ohne Evidence
  - gepufferter Postcheck fuer diese Contracts
  - container-spezifischer Safe-Fallback statt generischer
    `Verifizierte Ergebnisse:`-Antwort

Tests:

- neue Output-/Grounding-Regressionen fuer Container-Inventar
- neue Postcheck-/Leakage-Regressionen fuer Blueprint- und Binding-Drift

Akzeptanzkriterium:

- `welche Container hast du zur Verfuegung?`
  beantwortet laufende und gestoppte Container sichtbar, nicht nur Blueprints
- `welche Blueprints gibt es?`
  behauptet keine Runtime-Leere ohne `container_list`-Evidence
- `welcher Container ist gerade aktiv?`
  kippt nicht mehr in Diagnose-/Action-Spekulation

---

## Betroffene Dateien

Primaer:

- [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- [core/layers/control.py](<repo-root>/core/layers/control.py)
- [core/layers/output.py](<repo-root>/core/layers/output.py)
- [intelligence_modules/container_addons/loader.py](<repo-root>/intelligence_modules/container_addons/loader.py)
- [intelligence_modules/container_addons/taxonomy/20-query-classes.md](<repo-root>/intelligence_modules/container_addons/taxonomy/20-query-classes.md)
- [intelligence_modules/container_addons/taxonomy/30-answering-rules.md](<repo-root>/intelligence_modules/container_addons/taxonomy/30-answering-rules.md)

Sekundaer:

- [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)
- [core/container_state_utils.py](<repo-root>/core/container_state_utils.py)

Tests:

- [tests/unit/test_orchestrator_plan_schema_utils.py](<repo-root>/tests/unit/test_orchestrator_plan_schema_utils.py)
- [tests/unit/test_orchestrator_domain_routing_policy.py](<repo-root>/tests/unit/test_orchestrator_domain_routing_policy.py)
- [tests/unit/test_control_contract_flow.py](<repo-root>/tests/unit/test_control_contract_flow.py)
- [tests/unit/test_output_grounding.py](<repo-root>/tests/unit/test_output_grounding.py)

---

## Akzeptanzbild fuer den aktuellen Live-Fall

Prompt:

- `welche Container hast du zur Verfuegung?`

Zielbild:

- `resolution_strategy` bzw. `query_class`: `container_inventory`
- `is_fact_query = true`
- `suggested_tools = ["container_list"]`
- `final_execution_tools = ["container_list"]`
- keine implizite Umdeutung auf `request_container`
- keine reine Blueprint-Antwort
- sichtbare Antwort trennt mindestens:
  - laufende Container
  - installierte/gestoppte Container

---

## Empfohlene Reihenfolge

1. Block 4 - Addons als semantischen Resolver enger an `query_class` koppeln
   - **erledigt**
2. Block 5 - Output-/Antwortcontract fuer Container-Inventar nachziehen
   - **erledigt**
3. danach Live-Recheck fuer Inventar-, Blueprint- und Binding-Prompts
   - **erledigt** als lokaler Output-Live-Recheck mit Safe-Fallback-Nachzug
4. separaten Folgepfad fuer `container_request`-/Home-Start-/Routing-Drift
   weiterziehen

---

## Warum dieser Plan und nicht nur Addon-Prompting

Nur Addon-Prompting waere zu spaet im Pfad.

Wenn eine Inventarfrage bereits als:

- `active_container_capability`
- oder `request_container`

klassifiziert wurde, kann ein spaeter geladener semantischer Zusatzprompt die
falsche Toolwahl nur noch begrenzt heilen.

Darum gilt hier dieselbe Lehre wie beim Skill-Catalog:

- Code setzt frueh die Query-Klasse und Tool-Autoritaet
- Addons liefern flexible Semantik, Erklaerung und Antwortmodus

So bleibt das System:

- modellrobust
- testbar
- beobachtbar im Trace
- und trotzdem semantisch flexibel
