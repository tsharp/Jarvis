# Container Addons

Container Addons sind kleine, container- oder stack-spezifische Wissensdokumente
für `TRION shell`.

Ziel:
- kleiner stabiler Shell-Systemprompt
- containerbezogene Runtime-Fakten separat halten
- kommandospezifisches Wissen modular nachladbar machen
- 8B-Modelle nicht mit riesigen Core-Prompts überladen

Wichtig:
- Das ist **nicht** der allgemeine "model scan"- oder Dokument-Scan-Ordner.
- Diese Addons sind ein eigener Retrieval-Baustein für Container-/Shell-Kontext.
- Addons sollen kurz, operational und verifizierbar bleiben.

Empfohlene Struktur:

```text
intelligence_modules/container_addons/
  README.md
  ADDON_SPEC.md
  taxonomy/
    00-overview.md
    10-static-containers.md
    20-query-classes.md
    30-answering-rules.md
  templates/
    base-shell-addon.md
    gaming-headless-addon.md
  profiles/
    gaming-station/
      00-profile.md
      10-runtime.md
      20-diagnostics.md
      30-known-issues.md
```

Geplante spätere Nutzung:
- Shell-Controller bestimmt ein Container-Profil
- passende Addons werden per Tags/Metadaten ausgewählt
- daraus werden wenige relevante Abschnitte in den Shell-Kontext gezogen

Neue Trennung:
- `taxonomy/` enthaelt statisches Begriffs- und Antwortwissen fuer Containerfragen.
- `profiles/` enthaelt container- oder blueprint-spezifisches Wissen.
- Live-Zustaende wie `running`, `stopped`, `attached` oder `active in session`
  sind **nicht** in diesen Markdown-Dateien autoritativ.
- Laufzeitwahrheit muss aus Runtime-Tools kommen, nicht aus Addon-Text.

Kurzform:
- `list_container_blueprints` = was grundsaetzlich existiert / startbar ist
- `list_running_containers` = was gerade lebt

Diese beiden Dinge duerfen nicht in denselben Antworttopf geworfen werden.

Für neue Addons zuerst `ADDON_SPEC.md` lesen.
