# Container Addons

## Problem

TRION Shell soll auch mit kleineren Modellen brauchbar bleiben. Ein immer größerer Systemprompt wäre dafür die falsche Richtung:

- zu viel Tokenlast
- schwer wartbar
- zu viel generisches Linux-Wissen ohne Containerbezug

## Gewählte Richtung

Stattdessen wurde ein neues `container_addons`-System vorbereitet.

Idee:

- kleiner Shell-Kernprompt
- strukturierter Runtime-Kontext
- container- und stack-spezifische Markdown-Dokumente
- später Retrieval per Tags plus Embeddings

## Speicherort

Die Addons liegen bewusst nicht im allgemeinen Model-Scan-Ordner, sondern separat unter:

- `intelligence_modules/container_addons/`

## Gaming-Station als erster Testfall

Für `gaming-station` wurden vier erste Addon-Dateien eingeführt:

- `00-profile.md`
- `10-runtime.md`
- `20-diagnostics.md`
- `30-known-issues.md`

Diese Dokumente enthalten:

- Container-Identität
- Runtime-Topologie
- Diagnosepfade
- bekannte Fehlerbilder
- sinnvolle Prüfkommandos
- Dinge, die TRION vermeiden soll

Zusätzlich wurden wiederverwendbare Addons ergänzt:

- `generic-linux`
- `runtime-supervisord`
- `headless-x11-novnc`
- `apps-sunshine`
- `apps-steam-headless`

## Loader

Ein erster Loader wurde implementiert:

- Frontmatter wird aus Markdown-Dateien gelesen
- passende Dokumente werden über `blueprint_id`, `image_ref` und Tags vorgefiltert
- danach erfolgt ein lexical-first Ranking
- optional folgt ein leichtes Embedding-Refinement

Ziel:

- nicht blind alle Dateien an das Modell kippen
- sondern kleine, passende Ausschnitte auswählen

## Anbindung an TRION Shell

Im Shell-Step bekommt TRION jetzt zusätzlich:

- strukturierte Runtime-Fakten
- abgeleitete Container-Tags
- relevante Addon-Ausschnitte

Die Shell-Prompts wurden so gehärtet, dass Addon-Kontext und Runtime-Fakten Vorrang vor generischen Linux-Annahmen haben.

Ein sichtbarer Erfolg war:

- bei `noVNC blackscreen` nutzt TRION jetzt `supervisorctl status`
- und nicht mehr blind `systemctl`

## Zielbild

Später soll das System ausgebaut werden:

- mehr Profile pro Blueprint/Stack
- Addon-Registry im Blueprint-Kontext
- robustere Auswahl
- Embeddings stärker ergänzen
- eventuell von Usern erweiterbare Blueprint-spezifische Addons
