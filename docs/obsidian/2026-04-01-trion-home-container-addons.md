# TRION Home — Container Addons

Erstellt am: 2026-04-01
Status: **Umgesetzt**
Bezieht sich auf:

- [[04-Container-Addons]] — Addon-System Überblick
- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]] — Systemüberblick
- [[2026-04-05-container-query-klassentrennung-und-addon-contract-implementationsplan]] — neue Trennung zwischen statischem Containerwissen und Live-Zustaenden

---

## Update 2026-04-05 - Taxonomie-Split fuer statische Containerbegriffe

Das `container_addons`-System ist seit dem Container-Query-Umbau nicht mehr nur
ein Profilspeicher fuer einzelne Container, sondern auch Traeger fuer statische
Container-Taxonomie.

Neu dazugekommen:

- `intelligence_modules/container_addons/taxonomy/00-overview.md`
- `intelligence_modules/container_addons/taxonomy/10-static-containers.md`
- `intelligence_modules/container_addons/taxonomy/20-query-classes.md`
- `intelligence_modules/container_addons/taxonomy/30-answering-rules.md`

Neue Trennung:

- `profiles/` erklaert konkrete Container- oder Blueprint-Profile wie
  `trion-home` oder `gaming-station`
- `taxonomy/` erklaert Begriffe, Query-Klassen und Antwortregeln
- Live-Zustaende wie `running`, `stopped`, `attached` oder
  `active in session` bleiben weiterhin ausserhalb dieser Markdown-Dateien
  autoritativ und muessen aus Runtime-Tools kommen

Konsequenz fuer `trion-home`:

- das Profil unter
  [intelligence_modules/container_addons/profiles/trion-home](<repo-root>/intelligence_modules/container_addons/profiles/trion-home)
  bleibt statische Identitaets- und Workspace-Doku
- es ist **nicht** die primaere Quelle fuer Aussagen wie
  `trion-home laeuft gerade` oder
  `dieser Turn ist an trion-home gebunden`
- solche Aussagen muessen weiterhin ueber Session-State, `container_list` oder
  `container_inspect` verifiziert werden

---

## Motivation

TRION Home ist TRIONs persistenter Heimcontainer. Im Gegensatz zu Task-Containern
lebt dieser Container zwischen den Sessions — Dateien bleiben erhalten, Kontext bleibt erhalten.

Das Container-Addon-System (MD-Dateien mit Frontmatter) wurde bisher nur für
externe Blueprints wie `gaming-station` genutzt. Da TRION Home ein eigener Blueprint ist,
bekommt er jetzt denselben Mechanismus: TRION weiß beim Betreten des Containers
was dort verfügbar ist, wie der Workspace aufgebaut ist und welche Regeln gelten.

---

## Was bereits existiert (kein Duplikat nötig)

| System | Zuständig für |
|---|---|
| `home_memory.py` | Policy-gesteuertes Gedächtnis (`memory/notes.jsonl`) |
| `core/persona.py` | TRIONs Identität und Persona |
| `core/session_metrics.py` | Runtime-Telemetry (RAM, nicht persistent) |
| `core/digest/` | Daily/Weekly-Archivierung |
| Memory-Background | User-Kontext (danny, Präferenzen, Projekthistorie) |

Diese Systeme laufen außerhalb des Containers — keine Doppelung in den Addons.

---

## Addon-Dateien

**Pfad:** `intelligence_modules/container_addons/profiles/trion-home/`

| Datei | Scope | Inhalt |
|---|---|---|
| `00-profile.md` | `container_profile` | Identität, Blueprint-ID, Verzeichnisstruktur im Überblick |
| `10-runtime.md` | `runtime` | python:3.12-slim, was ist installiert, Netzwerk-Limitierung, init-less |
| `20-workspace.md` | `diagnostics` | Jedes Verzeichnis erklärt, Navigation, Workspace-Überblick-Befehle |
| `30-tools.md` | `safety` | Python Stdlib, Shell-Tools, Safety-Regeln für das persistente Volume |

Ergaenzende Taxonomie:

| Pfad | Rolle |
|---|---|
| `intelligence_modules/container_addons/taxonomy/00-overview.md` | Oberbegriffliche Trennung zwischen Blueprint, Runtime-Inventar, Binding und Capability |
| `intelligence_modules/container_addons/taxonomy/10-static-containers.md` | Statische Erklaerung wichtiger Systemcontainer |
| `intelligence_modules/container_addons/taxonomy/20-query-classes.md` | Query-Klassen fuer Inventory, Blueprint, Binding, Capability und Request |
| `intelligence_modules/container_addons/taxonomy/30-answering-rules.md` | Regeln gegen Vermischung von statischem Wissen und Live-Zustand |

---

## Workspace-Struktur

```
/home/trion/
├── memory/          — system-managed (home_memory.py) — nicht manuell bearbeiten
├── notes/           — schnelle Notizen, Ideen, Referenzen
├── projects/        — laufende Projekte mit README.md als Kontext-Anker
│   └── <name>/
├── scripts/         — selbst geschriebene Werkzeuge und Helfer
├── experiments/     — Ausprobieren ohne Erwartungen
├── creative/        — freie Outputs, generierte Texte, Konzepte
├── journal/         — persönliche Reflexion, ungefiltert, kein Policy-Guard
└── .config/         — Konfigurationsdateien
```

### Philosophie hinter der Struktur

- `memory/` ist gefiltertes Gedächtnis (Importance-Threshold, Policy) — vom System verwaltet.
- `journal/` ist **ungefilterte Reflexion** — TRION schreibt selbst rein, ohne Guard.
- `projects/` gibt laufenden Aufgaben Kontext über Session-Grenzen hinweg.
- `scripts/` verhindert dass TRION das Rad jedes Mal neu erfindet.
- `experiments/` und `creative/` geben Freiraum — kein Auftrag, kein Erwartungsdruck.

---

## Loader-Anbindung

Der Addon-Loader erkennt die Dateien automatisch über:

```yaml
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
```

TRION bekommt beim Betreten des Home-Containers die passenden Addon-Ausschnitte
als Kontext — ohne dass alle Dateien vollständig geladen werden müssen.

Seit dem Update 2026-04-05 liest der Loader ausserdem auch
`intelligence_modules/container_addons/taxonomy/`, damit statische
Containerbegriffe getrennt von konkreten Profilen verfuegbar bleiben.

---

## Nächste Schritte (Ideen)

- Loader-Integration testen: TRION Home starten, prüfen ob Addons korrekt selektiert werden
- Cronjob-Idee: TRION schreibt automatisch Journal-Eintrag nach jeder Session (für später)
- `projects/`-Konvention formalisieren: README.md-Template für neue Projekte
