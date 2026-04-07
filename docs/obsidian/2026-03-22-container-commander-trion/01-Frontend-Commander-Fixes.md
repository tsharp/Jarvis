# Frontend Commander Fixes

## Dashboard

Es gab mehrfach Scroll-Probleme im Container-Commander-Dashboard. Ursache war ein verschachteltes Flex-Layout mit fehlenden `min-height: 0`-Grenzen und später zusätzlich gestauchten Dashboard-Karten.

Wichtige Fixes:

- `min-height: 0` für zentrale Layout-Container gesetzt
- `.term-container` als sauber schrumpfbares Flex-Kind gehärtet
- direkte Kinder von `.dash-wrap` gegen ungewolltes `flex-shrink` abgesichert

Ergebnis:

- Dashboard scrollt wieder korrekt
- `Today Timeline` und `Continue Working` werden nicht mehr zusammengedrückt

## Logs + Shell

Das Logs-/Shell-Panel hatte mehrere Probleme:

- `Waiting for shell data...`
- `Waiting for log stream...`
- Wechsel zwischen aktiven Containern funktionierte nicht sauber
- fehlerhafte Zeilenumbrüche führten zu kaputter Shell-Formatierung

Umgesetzte Fixes:

- WS-/PTY-Handling im Backend stabilisiert
- Log-Following entkoppelt, damit der Event-Loop nicht blockiert
- lokale `xterm`-Assets statt externer CDN-Abhängigkeit
- xterm-Ausgabe auf saubere `\r\n`-Zeilenenden normalisiert
- TRION-Mehrzeilenausgaben ebenfalls auf xterm-taugliches Rendering umgestellt

Ergebnis:

- Live-Logs und Live-Shell funktionieren wieder
- Containerwechsel ist möglich
- Shell- und TRION-Ausgabe bleiben lesbar formatiert

## Stats und Sichtbarkeit

Im Container-Commander wurden zusätzliche operative Informationen ergänzt:

- Port-Anzeige in der Stats-Ansicht
- lesbare Dienstnamen statt nur `Port / TCP`
- `Open Desktop GUI`-Link für Container mit veröffentlichter noVNC-GUI

Nutzen:

- schneller Überblick, auf welchen Ports Dienste laufen
- direkter Einstieg in Sunshine-WebUI oder Desktop-GUI

## Bekannte betroffene Dateien

- `adapters/Jarvis/style.css`
- `adapters/Jarvis/static/css/terminal.css`
- `adapters/Jarvis/js/apps/terminal.js`
- `adapters/Jarvis/js/apps/terminal/xterm.js`
- `adapters/Jarvis/js/apps/terminal/containers.js`
- `adapters/Jarvis/js/apps/terminal/command-input.js`
- `container_commander/ws_stream.py`
- `adapters/Jarvis/nginx.conf`
