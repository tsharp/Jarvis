# Auto Clarify Package

Dieses Unterpaket ist der Zielort fuer kontrollierte Selbstklaerung im
Task-Loop.

Ziel:
- fehlende Informationen nicht sofort an den User zurueckspielen
- zuerst pruefen, ob TRION sie selbst entdecken, ergaenzen oder sicher
  aufloesen darf
- dabei klare Safety- und Authority-Grenzen zwischen
  Self-Discovery, Self-Completion, Secret-Resolution, User-Rueckfrage und
  Blockade erzwingen

Wofuer das gedacht ist:
- Container:
  Blueprints selbst auswaehlen, sichere Defaults setzen, Discovery vor
  `request_container`
- Skills:
  Allowlist-konforme Pakete und Skill-Metadaten selbst vervollstaendigen
- Cronjobs:
  sichere Schedule-/Policy-Pruefung vor Create/Update
- MCPs:
  registrierte/lesende Faelle zuerst selbst klaeren
- Secrets:
  explizit erlaubte Secrets gezielt ueber `get_secret("NAME")` aufloesen

Abgrenzung:
- `read_first_policy.py` entscheidet, ob zuerst sichere Discovery noetig ist
- `auto_clarify/` entscheidet, ob fehlende Felder selbst geklaert oder
  ergaenzt werden duerfen
- `step_runtime/` fuehrt nur bereits geklaerte Aktionen aus

Geplante Module:
- `contracts.py`
- `policy.py`
- `domain_dispatch.py`
- `safety_gates.py`
- `parameter_completion.py`
- `secret_resolution.py`
- `capabilities/container.py`
- `capabilities/skill.py`
- `capabilities/cron.py`
- `capabilities/mcp.py`
- `capabilities/generic.py`

Erste feste API:
- `AutoClarifyMode`
- `AutoClarifyAutonomyLevel`
- `AutoClarifySource`
- `AutoClarifyValueSource`
- `MissingField`
- `ResolvedField`
- `AutoClarifyBlocker`
- `AutoClarifyAction`
- `AutoClarifyDecision`

Wichtige Contract-Idee:
- `AutoClarifyDecision` beschreibt nur, was entschieden wurde
- `AutoClarifyAction` beschreibt nur die vorbereitete naechste Massnahme
- die spaetere Runner-/Resolver-Integration fuehrt diese Massnahme aus
- Capability-Handler liefern also orchestrator-kompatible Entscheidungen,
  triggern den Orchestrator aber nicht direkt

Safety-Gate-Modell:
- zuerst harte Blocker, z. B. Policy-Verstoss, unbekanntes Secret,
  nicht erlaubtes Paket
- danach Kandidaten-Scoring
- Default-Schwellen:
  - `>= 0.80` und Margin `>= 0.10` => autonom weiter
  - darunter => erst Recheck / Discovery vertiefen
  - nach Recheck ohne klaren Sieger => User fragen
- die Safety-Gates entscheiden damit nicht nur ueber "ja/nein", sondern
  ueber:
  - `self_execute`
  - `recheck`
  - `ask_user`
  - `block`

Aktueller erster Laufweg:
- `domain_dispatch.py` sammelt domain-spezifische Vorschlaege
- `policy.py` normalisiert diese Vorschlaege und wendet die Safety-Gates an
- Container hat bereits einen ersten spezialisierten Proposal-Pfad
- alle anderen Faelle laufen vorerst ueber den generischen Fallback

Aktuelle Parameter-Completion:
- `parameter_completion.py` ergaenzt im Container-Pfad erste sichere Defaults
- aktuell nur fuer `request_container` / `python_container`
- erste Defaults:
  - `python_version=3.11`
  - `dependency_spec=none`
  - `build_or_runtime=runtime`
- Ziel: Discovery und User-Rueckfrage nur noch fuer wirklich offene Felder,
  nicht fuer triviale Safe-Defaults
