---
id: gaming-station-known-issues
title: Gaming Station Known Issues
scope: known_issues
applies_to:
  blueprint_ids: [gaming-station]
  image_refs: [josh5/steam-headless:latest]
  container_tags: [gaming, headless-gui, steam, sunshine]
tags:
  - known-issues
  - steam
  - sunshine
  - novnc
  - x11
  - flatpak
  - nvidia
  - seccomp
priority: 85
retrieval_hints:
  - known issue
  - common failure
  - workaround
  - container exits
  - exit code 32
  - flatpak
  - seccomp
  - nvidia not found
  - black screen
  - sunshine crash
  - steam update loop
commands_available: []
confidence: high
last_reviewed: 2026-03-22
---

# Summary

Bekannte Fehlerbilder fur `gaming-station`. Jedes Muster enthalt:
- Symptom
- Ursache
- sicherer nachster Schritt

## Bekannte Fehlerbilder

---

### 1. Container startet, beendet sich sofort mit exit_code=32

**Symptom**: Container lauft kurz, dann exit. Logs enden mit Fehler in `80-configure_flatpak.sh`.

**Ursache**: Flatpak-Konfiguration im Init-Skript benotigt erweiterte Kernel-Capabilities.
Ohne `seccomp=unconfined` schlagt das Init-Skript fehl.

**Sicherer nachster Schritt**:
- Host-seitig prufen ob `security_opt: seccomp=unconfined` im Blueprint/Compose gesetzt ist.
- **Kein Workaround innerhalb des Containers moglich** — muss am Blueprint behoben werden.
- TRION soll dieses Problem melden und nicht selbst beheben.

---

### 2. Nvidia GPU nicht erkannt / Sunshine ohne Hardware-Encoding

**Symptom**: Sunshine startet, aber kein Hardware-Encoding verfugbar. Oder `nvidia-smi` schlagt fehl.

**Ursache**: `NVIDIA_VISIBLE_DEVICES` oder `NVIDIA_DRIVER_CAPABILITIES` nicht korrekt gesetzt.

**Prufung**:
```bash
echo $NVIDIA_VISIBLE_DEVICES       # muss: all
echo $NVIDIA_DRIVER_CAPABILITIES   # muss: all (oder compute,video,utility)
nvidia-smi 2>&1 | head -5
```

**Sicherer nachster Schritt**:
- Wenn env-Variablen fehlen: Blueprint prufen, Container neu starten mit korrekten Werten.
- TRION soll keine Runtime-Env-Patches versuchen.

---

### 3. noVNC zeigt schwarzen Bildschirm

**Symptom**: Browser verbindet sich mit noVNC (Port 47991), aber nur schwarzer Hintergrund.

**Mogliche Ursachen** (in Reihenfolge prufen):
1. Container noch nicht vollstandig gebootet (xfce4-session noch nicht fertig)
2. xfce4-session ist abgesturzt
3. x11vnc hat Verbindung zu X11 verloren
4. Auflosungskonflikt

**Prufung**:
```bash
supervisorctl status
ps -ef | grep -E 'xfce4-session|x11vnc' | grep -v grep
supervisorctl tail x11vnc stdout
```

**Sicherer nachster Schritt**:
- Zuerst 30–60s warten und neu prufen (langer Boot-Vorgang normal).
- Wenn die Desktop-Session fehlt: `supervisorctl restart desktop`
- Wenn x11vnc fehlt: `supervisorctl restart x11vnc`
- **Nicht**: x11vnc und Xorg gleichzeitig neu starten — Schritt fur Schritt.

---

### 4. Sunshine sturzt nach kurzer Zeit ab / startet nicht

**Symptom**: Sunshine-Prozess lauft kurz, dann gone. Oder WebUI nie erreichbar.

**Mogliche Ursachen**:
- GPU nicht verfugbar (siehe Issue #2)
- Portkonflikt auf 47990/47989
- Fehlende Konfigurationsdatei

**Prufung**:
```bash
supervisorctl tail sunshine stdout
ss -ltnup | grep -E '47989|47990'
ls ~/.config/sunshine/ 2>/dev/null || ls /config/sunshine/ 2>/dev/null
```

**Sicherer nachster Schritt**:
- Log zuerst lesen — Ursache oft direkt erkennbar.
- Bei GPU-Fehler: Blueprint-Env prufenn, nicht Sunshine-Config anfassen.
- Bei Portkonflikt: anderen Prozess auf dem Port identifizieren.

---

### 5. Steam-Installer blockiert mit GUI-Dialog

**Symptom**: Steam startet, aber bleibt im Installer-Fenster stehen. Kein Spielzugriff.

**Ursache**: Erststart oder Update — Steam zeigt UI-Dialog, der Benutzerinteraktion braucht.

**Prufung**:
```bash
ps -ef | grep steam | grep -v grep
xdotool search --name "Steam" 2>/dev/null
```

**Sicherer nachster Schritt**:
- Benutzer uber noVNC manuell weiterklicken lassen.
- **TRION soll Steam-GUI nicht automatisch durch `xdotool click` steuern** — riskant, kann falsche Buttons treffen.
- Wenn Steam in Update-Schleife: `~/.steam/` oder `~/.local/share/Steam/` prufen ob Schreibrechte stimmen.

---

### 6. Supervisor zeigt Dienst als RUNNING, aber Prozess reagiert nicht

**Symptom**: `supervisorctl status` zeigt `RUNNING`, aber Port ist zu oder noVNC leer.

**Ursache**: Prozess ist in zombieartigem Zustand oder hat intern einen Fehler.

**Prufung**:
```bash
ps -ef | grep <dienstname> | grep -v grep    # Prozess wirklich da?
ss -ltnup | grep <port>                      # Port wirklich offen?
supervisorctl tail <dienst> stdout           # Was sagt der Dienst?
```

**Sicherer nachster Schritt**:
- Erst Log lesen, dann entscheiden ob Restart sinnvoll ist.
- `supervisorctl restart <dienst>` nur wenn klar ist was schief lauft.

---

## Recovery-Reihenfolge (allgemein)

1. `supervisorctl status` — Gesamtbild
2. Prozess wirklich vorhanden? (`ps -ef`)
3. Port offen? (`ss -ltnup`)
4. Log gelesen? (`supervisorctl tail <dienst> stdout`)
5. Erst dann: gezielter `supervisorctl restart`
6. Niemals: mehrere Dienste gleichzeitig neu starten ohne Prufung

## Avoid

- `supervisorctl restart` ohne vorherigen Log-Check
- x11vnc und Xorg gleichzeitig neu starten
- Steam-GUI-Automation via xdotool ohne vorherige Fenster-Prufung
- GPU-Env-Variablen innerhalb des Containers patchen (wirkt nicht persistent)
- Auf exit_code=32 mit Container-internen Workarounds reagieren (muss Host-seitig gelost werden)
- Annahmen uber Dienst-Zustand ohne Verifikation — immer prufen bevor man handelt
