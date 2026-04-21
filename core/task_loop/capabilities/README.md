# Capability Packages

Dieses Paket ist der Zielort fuer domain-spezifische Task-Loop-Logik.

Der Loop-Core bleibt generisch:
- Input
- Kontext sammeln
- Plan
- Aktion
- Verifikation
- Replan

Capability-spezifische Regeln gehoeren nicht in `prompting.py`, sondern in
eigene Pakete unter `capabilities/`.

Aktueller Zielpfad:
- `container/`
  Container-/Python-Container-spezifische Kontext-, Discovery-, Parameter- und
  Recovery-Logik.
