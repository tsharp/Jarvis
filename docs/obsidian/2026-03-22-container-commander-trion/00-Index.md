# Jarvis Container Commander + TRION Doku

Erstellt am: 2026-03-22

Diese Notizen fassen die Arbeiten rund um `Container Commander`, `gaming-station`, `TRION shell`, `StorageBroker` und die neuen `container_addons` zusammen.

Archivhinweis 2026-04-01:

- Der fruehere `gaming-station`-/Gaming-Container-Arbeitszweig ist gestoppt und archiviert.
- Die dazugehoerigen Detailnotizen liegen jetzt gesammelt unter [[Archiv/2026-04-gaming-station/00-Archiv-Index|Archiv/2026-04-gaming-station]].

Ergänzung vom 2026-03-23:

- `gaming-station` streamt jetzt nicht mehr mit Sunshine im Container, sondern über hostnahes Sunshine.
- Der Moonlight-Pairing-Hänger wurde auf Host-Sunshine-Version/Pairing-Verhalten eingegrenzt und mit einem älteren offiziellen Build umgangen.
- Host-Display und Steam Big Picture wurden auf einen sauberen `1920x1080`-Pfad gebracht.
- `gaming-station` wird beim normalen Commander-Stop standardmäßig erhalten statt gelöscht.
- `gaming-station` wird jetzt zusätzlich als optionales `composite addon` für den Marketplace vorbereitet statt fest im TRION-Core verdrahtet.
- Für dieses Composite-Addon existiert jetzt ein sicherer `shadow install`-Pfad, der Host-Dateien materialisiert, ohne den laufenden Sunshine-Service zu überschreiben.
- Der Marketplace-Bundlepfad kann jetzt auch die `container_addons` von `gaming-station` mit exportieren und beim Import wieder installieren.
- Ein echter GitHub-basierter `catalog -> bundle -> import`-Installpfad für `gaming-station` wurde erfolgreich verifiziert.
- Ein neuer Architektur-Befund ist dokumentiert: `Control Layer: Approved` kann bei Container-Requests weiterhin in einen generischen Tool-/Evidence-Fallback kippen; siehe [[2026-04-01-control-authority-drift-approved-fallback-container-requests]].

## Inhalt

- [[01-Frontend-Commander-Fixes]]
- [[03-TRION-Shell-Mode]]
- [[04-Container-Addons]]
- [[05-Open-Issues-Next-Steps]]
- [[08-TRION-Chatflow-Smalltalk-vs-Facts-Plan]]
- [[09-TRION-Chatflow-Index]]
- [[19-TRION-Planmodus-und-Sequential-Thinking-Analyse]]
- [[20-TRION-Chat-Shell-Memory-und-Kontext-Analyse]]
- [[21-TRION-Chat-Shell-CIM-und-Control-Analyse]]
- [[2026-04-01-control-authority-drift-approved-fallback-container-requests]]
- [[22-TRION-Chat-Shell-Implementationsplan]]
- [[23-Runtime-Hardware-Modul-Implementationsplan]]
- [[24-Runtime-Hardware-v0-Installationsvertrag]]
- [[25-Runtime-Hardware-v0-Containerbauplan]]
- [[26-Runtime-Hardware-block_device_ref-Implementationsplan]]

## Archivierte Gaming-Station-Notizen

- [[Archiv/2026-04-gaming-station/02-Gaming-Station-Storage-Sunshine-noVNC|02-Gaming-Station-Storage-Sunshine-noVNC]] - gestoppt und archiviert
- [[Archiv/2026-04-gaming-station/06-Gaming-Station-Setup-Guide|06-Gaming-Station-Setup-Guide]] - gestoppt und archiviert
- [[Archiv/2026-04-gaming-station/07-Gaming-Station-GitHub-Package-Prep|07-Gaming-Station-GitHub-Package-Prep]] - gestoppt und archiviert
- [[Archiv/2026-04-gaming-station/18-Claude-Handoff-Gaming-Station-2026-03-24|18-Claude-Handoff-Gaming-Station-2026-03-24]] - gestoppt und archiviert

## Kurzfassung

- Scroll- und Layout-Probleme im Container-Commander-Dashboard wurden behoben.
- Das Logs-/Shell-Panel wurde stabilisiert, inklusive Containerwechsel und besserem xterm-Rendering.
- `gaming-station` wurde als echter Steam-Headless- + Sunshine-Testcontainer aufgebaut und spaeter gestoppt sowie archiviert.
- Die urspruengliche Container-Sunshine-Architektur wurde spaeter auf `Host Sunshine + Container Steam Bridge` umgebaut und ist heute nur noch archiviert dokumentiert.
- StorageBroker und Container Commander wurden für externe Storage-Pfade enger verdrahtet.
- `gaming-station` wird als Shop-/Marketplace-Paket mit `Blueprint + Host Companion + Binary Bootstrap` vorbereitet.
- `TRION shell` wurde als eigener Commander-Modus eingeführt.
- Der Shellmodus wurde mit Verifikation, Loop-Guard und strukturierter Exit-Summary gehärtet.
- Für container-spezifisches Shellwissen wurde ein neues `container_addons`-System vorbereitet und für `gaming-station` erstmals angebunden.

## Hauptziele dieser Ausbaustufe

1. Container im Commander besser sichtbar und steuerbar machen.
2. Einen realen Gaming-Container als Integrationsprobe für StorageBroker + Commander nutzen und den daraus entstandenen Verlauf archivieren.
3. TRION direkt im Container-Debugging nutzbar machen.
4. Shell-Wissen modular halten, statt riesige Systemprompts zu bauen.
