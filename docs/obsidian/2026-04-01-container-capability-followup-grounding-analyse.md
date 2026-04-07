# Container-Capability-Follow-up driftet noch zwischen Blueprint-Wissen, Runtime und Output-Grounding

Erstellt am: 2026-04-01
Zuletzt aktualisiert: 2026-04-01
Status: **Analyse abgeschlossen / Fix umgesetzt**
Bezieht sich auf:

- [[2026-04-01-control-authority-drift-approved-fallback-container-requests]] - behobener Start-/Clarification-Drift
- [[2026-04-01-control-authority-drift-container-clarification-implementationsanalyse]] - Analyse des Control-Vertrags
- [[2026-04-01-control-authority-drift-container-clarification-implementationsplan]] - Umsetzungsplan fuer den vorherigen Fix
- [[2026-04-01-container-capability-followup-grounding-fix]] - umgesetzter Fix fuer den aktiven Capability-Chatpfad
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]] - Folgeplan fuer Thinking/Control/Execution-Authority und UI-Sichtbarkeit
- [[2026-04-01-trion-home-container-addons]] - vorhandenes TRION-Home-Addon-Wissen
- [[04-Container-Addons]] - Zielbild des Addon-Systems

---

## Fixstatus

Die in dieser Analyse beschriebene Luecke wurde am 2026-04-01 umgesetzt.

Implementierungsnotiz:

- [[2026-04-01-container-capability-followup-grounding-fix]]

Kurzfassung des umgesetzten Pfads:

- deiktische Capability-Follow-ups ueber den aktiven Container werden jetzt explizit erkannt
- der Resolver priorisiert `container_inspect` statt `container_stats` plus generischem `exec_in_container`
- `container_addons` werden im normalen Chatpfad aus `blueprint_id` plus `image` geladen
- Sync und Stream injizieren diesen Block vor dem Output als Kontext und Grounding-Evidence

Damit beschreibt der Rest dieser Notiz den **urspruenglichen Root Cause** vor dem Fix.

---

## Anlass

Nach dem Fix fuer den Container-Startpfad funktioniert der eigentliche Start- und Clarification-Flow deutlich besser:

- `starte einmal bitte: TRION Home Workspace` fuehrt nicht mehr in einen generischen Grounding-Fallback
- der Follow-up `genau starte bitte: trion-home` startet den Container erfolgreich

Der naechste Folge-Intent bleibt aber instabil:

- User: `was kannst du in diesem container alles tun?`
- Thinking: `suggested_tools=["container_stats", "exec_in_container"]`
- finale Antwort: beschreibt den Container frei als Alpine-/shell-sandbox-Umgebung
- danach haengt der Stream eine `[Grounding-Korrektur]` mit echten Tool-Ergebnissen an

Damit ist der Start-Drift zwar behoben, der Capability-Follow-up fuer laufende Container aber noch nicht sauber grounded.

---

## Kurzdiagnose

Der verbleibende Fehler ist **kein weiterer Control-Drift**, sondern ein fehlender Capability-Contract fuer aktive Container im normalen Chatpfad.

Die Laufzeit kennt bereits:

- den aktiven Container
- den Blueprint `trion-home`
- vorhandene `container_addons` mit genau den gesuchten Informationen

Diese Wissensquelle wird fuer den normalen Chat-Orchestrator in diesem Fall aber nicht verwendet.
Stattdessen entsteht ein zu schwacher Tool-Pfad:

1. generische Toolwahl `container_stats` + `exec_in_container`
2. `exec_in_container` bekommt einen Dummy-Fallback-Befehl
3. das Modell fuellt die Wissensluecke mit generischen Linux-Annahmen
4. Output-Grounding kann nur noch am Ende sichtbar korrigieren

---

## Konkreter Fehlerlauf

### 1. Die Folgefrage wird nicht als blueprint-aware Capability-Query behandelt

Die Frage

- `was kannst du in diesem container alles tun?`

ist semantisch keine rohe Runtime-Statusabfrage, sondern eine Frage nach:

- Zweck des aktiven Containers
- bekannten Faehigkeiten
- Workspace-Struktur
- verfuegbaren Werkzeugen
- sinnvollen typischen Aktionen

Im aktuellen Chatpfad gibt es dafuer aber keinen eigenen Resolver.
Thinking faellt deshalb auf die generischen Runtime-Tools

- `container_stats`
- `exec_in_container`

zurueck.

### 2. Der vorhandene Home-Harden-Pfad greift hier nicht

Es existiert bereits ein spezieller Home-Info-Pfad in [core/orchestrator.py](<repo-root>/core/orchestrator.py#L2127):

- `_is_home_container_info_query()` verlangt explizite Marker wie `trion home`, `trion-home`, `home container`
- `_prioritize_home_container_tools()` greift nur fuer solche Home-Marker und nur bei `is_fact_query=True`

Die Folgefrage `was kannst du in diesem container alles tun?` referenziert aber den **aktuellen** Container nur deiktisch ueber:

- `diesem container`

Dadurch faellt sie aus diesem Override heraus, obwohl der aktive Container-Kontext bereits bekannt ist.

Folge:

- kein Home-/Blueprint-aware Routing
- kein gezieltes Lesen von Home-/Addon-Wissen

### 3. `container_addons` existieren, werden hier aber nicht genutzt

Der Loader ist vorhanden und kann passende Addon-Abschnitte ueber `blueprint_id`, `image_ref`, `instruction` und Tags selektieren: [loader.py](<repo-root>/intelligence_modules/container_addons/loader.py#L256).

Fuer `trion-home` liegt das passende Wissen bereits vor:

- [00-profile.md](<repo-root>/intelligence_modules/container_addons/profiles/trion-home/00-profile.md)
- [10-runtime.md](<repo-root>/intelligence_modules/container_addons/profiles/trion-home/10-runtime.md)
- [20-workspace.md](<repo-root>/intelligence_modules/container_addons/profiles/trion-home/20-workspace.md)
- [30-tools.md](<repo-root>/intelligence_modules/container_addons/profiles/trion-home/30-tools.md)

Dort steht bereits genau das, was fuer die Frage relevant gewesen waere:

- persistentes Home-Workspace statt Wegwerf-Sandbox
- `python:3.12-slim` / Debian-slim statt Alpine
- kein `jq`, kein `systemctl`, kein GUI-Stack
- Workspace-Struktur unter `/home/trion`
- Python/Stdlib, Shell-Tools und Safety-Regeln

Der entscheidende Befund:

- Im normalen Chat-Orchestrator wird `load_container_addon_context()` nicht benutzt.
- Die nachweisbare produktive Nutzung sitzt aktuell im Commander-Shellpfad: [containers.py](<repo-root>/adapters/admin-api/commander_api/containers.py#L897), [containers.py](<repo-root>/adapters/admin-api/commander_api/containers.py#L980), [containers.py](<repo-root>/adapters/admin-api/commander_api/containers.py#L1092).

Das heisst:

- `container_addons` sind im System vorhanden
- aber nicht Teil des normalen Capability-Reply-Pfads im Chat

### 4. Der generische `exec_in_container`-Fallback ist fuer Capability-Fragen zu schwach

Wenn `exec_in_container` ohne spezifischen Host-Runtime-Fall gebaut wird, verwendet der Orchestrator nur:

- `echo 'Container ready'`

in [core/orchestrator_tool_args_utils.py](<repo-root>/core/orchestrator_tool_args_utils.py#L84).

Das ist fuer diese Frage praktisch wertlos:

- kein Blueprint-Nachweis
- keine Toolliste
- keine Paket-/Runtime-Inspektion
- keine Workspace-Inspektion
- keine Identitaets-/Zweck-Info

`container_stats` liefert zwar echte Ressourcendaten, aber ebenfalls nicht:

- Zweck
- Runtime-Typ
- Workspace-Faehigkeiten
- Blueprint-spezifische Tools

Damit bleibt zwischen Userfrage und echter Tool-Evidence eine inhaltliche Luecke, die das Modell selbst fuellt.

### 5. Output-Grounding korrigiert nur am Ende sichtbar, statt den Pfad vorher zu haerten

Der Output-Precheck verlangt fuer Fact-Queries mit Toolvorschlaegen weiter Evidence: [output.py](<repo-root>/core/layers/output.py#L576).

Im Stream-Pfad wird die Antwort aber zunaechst normal gestreamt.
Wenn der Postcheck spaeter Abweichungen entdeckt, wird im Tail-Repair-Modus nur noch eine sichtbare Korrektur angehaengt: [output.py](<repo-root>/core/layers/output.py#L1516).

Das fuehrt genau zu dem Live-Effekt:

1. erst freie, teilweise halluzinierte Capability-Erklaerung
2. danach `[Grounding-Korrektur]`
3. darunter die echten Tool-Rohdaten

Damit ist der Guard formal aktiv, aber UX-seitig wirkt der Ablauf weiterhin wirr.

---

## Was hier konkret falsch laeuft

### A. Falsche Autoritaetsquelle fuer diese Fragetype

Bei `was kannst du in diesem container alles tun?` sollte die primaere Quelle nicht sein:

- generische Laufzeitprobe mit Default-Exec

sondern:

- aktiver Containerkontext
- Blueprint-Identitaet
- strukturierte `container_addons`
- optional ergaenzende Runtime-Verifikation

Der Chatpfad behandelt die Frage derzeit aber eher wie:

- "mach eine allgemeine Laufzeitabfrage und formuliere daraus eine Antwort"

statt wie:

- "erklaere den aktiven Container anhand seiner bekannten Identitaet und validiere nur die noetigen Runtime-Fakten"

### B. Deiktische Follow-ups werden nicht auf den aktiven Container aufgeloest

Der Container-State wird nach `request_container` korrekt gemerkt.
Trotzdem fuehrt ein Folge-Intent mit:

- `diesem container`

nicht in einen aktiven-container-aware Capability-Pfad.

Es fehlt also ein Resolver der Fragen wie:

- `was kannst du in diesem container`
- `wofuer ist er da`
- `was ist hier installiert`
- `welche tools hast du hier`

zuerst gegen den **aktuellen Containerzustand** und dessen Blueprint aufloest.

### C. Addon-Wissen ist operativ vorhanden, aber architektonisch falsch angebunden

Das Addon-System ist heute effektiv ein Wissensbaustein fuer:

- `TRION shell`
- Commander-Debug-/Shell-Workflows

Nicht aber fuer:

- normale Chat-Antworten ueber einen aktiven Container

Damit existiert ein Wissens-Silo:

- dieselben Containerfakten sind im System vorhanden
- aber der normale Chat nutzt sie nicht

### D. Grounding repariert Symptome, nicht die Auswahl der Wissensquelle

Der aktuelle Guard verhindert teilweise schlimmere Halluzinationen, aber zu spaet.
Er verhindert nicht, dass der falsche Wissenspfad gewaehlt wird.

Der eigentliche Fehler passiert frueher:

- bei Intent-Aufloesung
- bei Tool-/Kontextwahl
- bei der fehlenden Blueprint-/Addon-Einspeisung

---

## Warum die gegebene Antwort fachlich inkonsistent war

Die Live-Antwort behauptete sinngemaess:

- Alpine-basierte Shell-Umgebung
- shell-sandbox
- `curl`, `jq` und Standard-Linux-Utilities

Das kollidiert direkt mit dem dokumentierten `trion-home`-Profil:

- [10-runtime.md](<repo-root>/intelligence_modules/container_addons/profiles/trion-home/10-runtime.md) beschreibt Debian slim / `python:3.12-slim`
- dort steht explizit, dass `jq` **nicht** vorinstalliert ist
- [00-profile.md](<repo-root>/intelligence_modules/container_addons/profiles/trion-home/00-profile.md) beschreibt den Container als persistenten Arbeitsraum, nicht als generische Wegwerf-Sandbox

Die Antwort war also nicht nur unvollstaendig, sondern nutzte nachweisbar die falsche mentale Vorlage fuer den aktiven Container.

---

## Root Cause in einem Satz

Der normale Chat besitzt noch keinen verbindlichen **active-container capability resolution path**, der deiktische Folgefragen ueber den aktuellen Container zuerst auf Blueprint-Identitaet und `container_addons` mappt und erst danach mit Runtime-Tools verifiziert.

---

## Einordnung gegenueber dem vorherigen Fix

Der vorige Fix hat den Container-Startvertrag stabilisiert:

- Clarification statt generischem Evidence-Fallback
- Control als staerkere Autoritaet fuer Start-/Routing-Entscheidungen

Der neue Befund liegt eine Schicht spaeter:

- nach erfolgreich gestarteter Runtime
- bei der semantischen Selbstauskunft ueber den aktiven Container

Es handelt sich daher um einen **neuen separaten Contract-Gap**, nicht um denselben Bug in anderer Form.

---

## Architekturelle Schlussfolgerung

Fuer Folgefragen ueber einen laufenden Container braucht der Chatpfad eine feste Reihenfolge:

1. aktiven Container aus State aufloesen
2. Blueprint/Identitaet bestimmen
3. passende `container_addons` laden
4. nur die noetigen Runtime-Tools zur Verifikation oder Anreicherung ziehen
5. Antwort aus diesen Quellen bauen, nicht aus generischen Linux-Annahmen

Solange dieser Contract fehlt, bleibt der Ablauf zwar teilweise guard-bedeckt, aber im Ergebnis:

- zu modellgetrieben
- zu wenig deterministisch
- zu leicht halluzinierend
- im Stream sichtbar wirr durch nachtraegliche Grounding-Korrektur

---

## Fazit

Das Problem ist **nicht**, dass TRION "zu wenig autonom denkt".
Das Problem ist, dass das System fuer diese Fragetype die falsche Wissensquelle priorisiert.

`container_addons` waeren hier sehr wahrscheinlich die richtige primaere Quelle gewesen.
Aktuell sind sie fuer normale Chat-Follow-ups ueber aktive Container aber noch nicht in den Orchestrator-Contract eingebunden.
