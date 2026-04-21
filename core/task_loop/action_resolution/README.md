# Action Resolution Package

Dieses Paket ist der vorgesehene Ort fuer die generische Uebersetzung von
Task-Loop-Planung in konkrete, naechste Massnahmen.

Ziel:
- zwischen `planner/` und `step_runtime/` eine eigene Schicht fuer
  Aktionsmaterialisierung einziehen
- sichere Self-Discovery vor vorschneller User-Rueckfrage bevorzugen
- capability-spezifische Resolver fuer Container, Skills, MCPs, Cronjobs und
  generische Loop-Anfragen an einen gemeinsamen Core anschliessen

Was hier spaeter hinein soll:
- generische Action-Resolution-Vertraege
- Read-first-/Discovery-Policy
- Auto-Clarify-/Self-Discovery-Policy
- Recovery-zu-naechster-Aktion-Uebersetzung
- Domain-Dispatch zu capability-spezifischen Resolvern

Erste feste API:
- `contracts.py`
  `ActionResolutionMode`, `ActionResolutionSource`,
  `ResolvedLoopAction`, `ActionResolutionDecision`
- `resolver.py`
  `resolve_next_loop_action(...)` als gemeinsamer Entry-Point
- `read_first_policy.py`
  generische Read-first-Helfer fuer Container, Skills, Cronjobs, MCPs und
  tool-gesteuerte Default-Faelle
- `auto_clarify/`
  vorbereitete Zielstruktur fuer kontrollierte Selbstklaerung,
  Parameter-Completion, Secret-Resolution und capability-spezifische
  Autonomie-Regeln

Aktueller Stand:
- nur Basissurface, noch keine echte Domain- oder Recovery-Logik
- Default-Verhalten:
  vorhandene Schritt-Metadaten (`suggested_tools`, `requested_capability`,
  `capability_context`) als ausfuehrbare Aktion weiterreichen
  oder sonst explizit `resolved=False` zurueckgeben
- Read-first-Verhalten:
  wenn ein Schritt nur Action-Tools oder gemischte Query-/Action-Tools traegt,
  kann die Policy bereits einen sicheren Discovery-Schritt davor bevorzugen

Abgrenzung:
- `planner/` beschreibt, *welche* Schritte es gibt
- `action_resolution/` entscheidet, *welche konkrete sichere Aktion* als
  naechstes daraus materialisiert wird
- `step_runtime/` fuehrt die bereits aufgeloeste Aktion aus

Geplante Module:
- `contracts.py`
- `resolver.py`
- `read_first_policy.py`
- `recovery_resolution.py`
- `domain_dispatch.py`

Unterpakete:
- `auto_clarify/`
  Zielort fuer autonome Self-Discovery-, Parameter-Completion- und
  Secret-Resolution-Regeln mit eigenen Safety-Gates, Domain-Dispatch und
  Capability-Handlern
