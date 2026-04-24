---
Tags: [TRION, Architecture, Executor, Sandbox, Skills]
aliases: [Tool Executor, skill_runner, mini_control_core]
---

# ⚙️ Tool Executor (Die Sandbox)

Das System unter `/tool_executor/` ist das Herzstück für alle Coder- und KI-Interaktionen in TRION. Dies ist die **Layer 4 Execution Runtime**. Es ist das *einzige* Modul im gesamten System, das berechtigt ist, Skripte (Skills) auf die Festplatte zu schreiben und auszuführen.

## 🏗️ 1. Die Sandbox-Sicherheit (`skill_runner.py`)

Wenn TRION Python-Code ausführt, läuft dieser Code in einer extrem abgeriegelten Sandbox:
- **Blocked Builtins:** Befehle wie `eval()`, `exec()`, oder `open()` sind deaktiviert. Die KI kann also keine beliebigen Dateien auf deinem Host-System überschreiben.
- **Module Whitelist:** Die KI darf nur erlaubte Pakete importieren (z.B. `requests`, `numpy`, `json`). Jeglicher Import von `os`, `sys`, oder `subprocess` führt sofort zum Abbruch (`Security violation`).
- **Secret Management:** Die KI kann Secrets abrufen (z.B. Wetter API Key), aber sie greift über eine speziell injizierte `get_secret("WEATHER_API_KEY")` Methode darauf zu. So sieht das LLM den Klartextschlüssel eigentlich nie beim Prompen, sondern der Schlüssel wird erst im Bruchteil einer Sekunde beim Ausführen in der Sandbox eingefügt!

## 🤖 2. Autonome Code-Reparatur (`mini_control_core.py`)

Das Highlight des Executors ist der **Mini Control Layer** (`process_autonomous_task`). 
Wenn der User eine Anfrage stellt, für die es noch keinen Code gibt:
1. Der Executor schickt das Problem an ein lokales Code-LLM (z.B. `qwen2.5-coder`).
2. Generierter Code wird sofort durch den `SecretScanner` gejagt, um zu gucken, ob die KI aus Versehen harte Passwörter in den Code geschrieben hat.
3. Danach folgt ein Testlauf.
4. **Auto-Repair:** Bricht der Code mit einem Fehler ab, sammelt der `mini_control_core` den Stacktrace und schickt ihn zurück an das Modell("Hier gibt es einen Syntax-Error, behebe ihn!") – und zwar bevor der User überhaupt merkt, dass es ein Problem gab!

## 🛡️ 3. Verträge (`api.py` & `contracts/`)

Jeder API-Rundruf (egal ob von TRION oder von extern) wird gegen harte JSON-Schemas (Contracts) validiert. Wenn ein Payload nicht den strikten Richtlinien entspricht, weigert sich der Executor, den neuen Skill zu speichern.

---

## 📈 Fazit für das Refactoring

Im Gegensatz zum *Memory System* und der *Config*, ist der Tool Executor **fantastisch entkoppelt**! Er läuft als sauberer Microservice (`FastAPI`) und vertraut niemandem – auch nicht dem eigenen System-Orchestrator. 

**Einziges Risiko:** Die `mini_control_core.py` ist mittlerweile 1800+ Zeilen lang. Hier ist extrem viel RAG- und Intent-Parsing-Logik ("Was wollte der User tun?") verbaut, die eigentlich in den KI-Layer und nicht in die Laufzeitumgebung (Executor) gehört. Dieses Modul ist gerade dabei, zum nächsten God-Object zu mutieren.
