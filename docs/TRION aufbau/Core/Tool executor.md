---
Tags: [TRION, Layer-4, Sandbox, Security]
aliases: [Tool Executor, Layer 4, tool_executor/api.py]
---

# 🔨 Layer 4: Tool Executor (`tool_executor/api.py`)

> [!info] Zusammenfassung
> Der Executor ist kein kognitiver "Layer" (wie [[Thinking]] oder [[Output]]), sondern ein eigenständiger kleiner Webserver (gebaut mit FastAPI, läuft auf Port 8000). Er fungiert als "Execution Runtime" und exklusiver Side-Effects Provider.

**Was extrem positiv ist:**
- **Single Control Authority:** Er weigert sich Skripte auszuführen, sofern kein gültiges Zertifikat (`control_decision`) vom **Control Layer** (`SKILL_CONTROL_AUTHORITY=skill_server`) vorliegt.
- **Sandbox:** Er baut sich selbstständig virtuelle Python-Umgebungen (`_ensure_executor_venv`) und installiert dort isoliert Pakete.

---

## 🔍 Das Architektur-Rätsel: Warum agiert Output als Executor?

Wir haben gesehen, dass [[Layer 3 (Output)]] eigenmächtig Tools aufruft. Der Grund dafür steht im Tool Executor Code:

> [!caution] Der Tool Executor ist kein universeller Tool-Ausführer!
> Er ist fast ausschließlich ein isolierter Ausführer für *generierte Python-Skills* (`/v1/skills/run`, `create`, `install_package`). 
> Wenn das System simple **Standard-Tools** braucht (wie "Suche in der Datenbank" oder "Prüfe laufende Container"), werden diese vom `mcp.hub` via [[Orchestrator]] ausgeführt, **nicht** vom Tool Executor!

### Begriffs-Trennung
1. **Standard-Tools:** Werden vom [[Orchestrator]] über die MCP-Telefonzentrale an die zuständigen MCP-Server weitergeleitet.
2. **Python Skills (User-Code):** Werden von Layer 4 (Tool Executor) im sicheren Sandkasten isoliert ausgeführt.

---

## 🕸️ Verbindungen nach außen

**Inbound (Wer ruft ihn auf?):**
- Eingehende HTTP-Anfragen, in der Regel gesteuert durch die MCPs (z. B. den `skill-server`) oder den [[Orchestrator]].

**Outbound (Was ruft er auf?):**
- **Das Betriebssystem:** Führt massiv Konsolen-Befehle aus (`subprocess.run`), um virtuelle Umgebungen (`venv`) zu erstellen und Pakete runterzuladen (`pip install`).
- **Die Skill-Engine:** Reicht den Code an den `skill_runner` und den `skill_installer` weiter.
- **Externe Registries:** Sendet Requests (`httpx`) ins Netzwerk, um Skills von außen herunterzuladen (`/v1/skills/install`).