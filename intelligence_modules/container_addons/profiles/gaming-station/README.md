# Gaming Station Addons

Dieser Ordner ist für `gaming-station`-spezifische Shell-Addons reserviert.

Empfohlene Dateien:

- `00-profile.md`
- `10-runtime.md`
- `20-diagnostics.md`
- `30-known-issues.md`

Claude kann diese Dateien direkt nach `ADDON_SPEC.md` erzeugen.

Wichtige Live-Fakten aus dem aktuellen Container-Setup:

- Blueprint: `gaming-station`
- Image: `josh5/steam-headless:latest`
- Init: `supervisord`
- Desktop: `XFCE`
- X11: `Xorg`
- noVNC/Websockify: intern `8083`, veröffentlicht als `47991`
- Sunshine Web UI: `47990`
- Sunshine HTTP: `47989`
- Steam / Sunshine / X11 / x11vnc laufen im selben Container

Wichtige TRION-Fallstricke:

- `systemctl` ist hier meist falsch
- GUI-Aktionen dürfen nicht blind wiederholt werden
- noVNC-Black-Screen heißt nicht automatisch, dass `x11vnc` oder `Xorg` down sind
