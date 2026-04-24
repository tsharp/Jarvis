---
Tags: [TRION, Architecture, Utils, Ollama, Parsing]
aliases: [Utils Module, json_parser, workspace, ollama_manager]
---

# 🛠️ Utils (Die Helferlein-Bibliothek)

Das `utils/` Verzeichnis wirkt auf den ersten Blick wie eine gewöhnliche Sammlung von Helper-Funktionen, beherbergt jedoch ein paar extrem mächtige "Defensive Programming"-Patterns. Da LLMs oft unberechenbar sind, fangen diese Skripte Fehler ab, bevor sie das restliche System crashen.

## 🏗️ Kernkomponenten

### 1. Robustes JSON-Parsing (`json_parser.py`)
LLMs generieren oft kaputtes JSON (z.B. ein Komma zu viel am Ende, gepackt in Markdown-Blöcke oder unquotierte Keys). Ein normaler `json.loads` würde sofort abstürzen.
Der `safe_parse_json` führt eine "**5-Stufen-Rettung**" durch:
1. Reguläres Parsen.
2. Suchen nach der ersten `{` und letzten `}`.
3. Extrahieren aus Markdown (` ```json {...} ``` `).
4. Auto-Repair-Regex (Entfernen von trailing commas, Fixen von Single Quotes).
5. Brutaler Regex-Fallback, der hart Key-Value-Paare via RegExp zusammenschustert.

### 2. Ollama Compute Cluster (`ollama_endpoint_manager.py`, `role_endpoint_resolver.py`)
TRION ist nicht einfach mit einem LLM verbunden. TRION hat Cluster-Support.
Diese Utils verwalten **Endpoint Routing**. Es gibt verschiedene Rollen (`thinking`, `control`, `output`, `tool_selector`). 
Der Manager fragt live per Docker ab, welche Container (`gpu0`, `gpu1`, `cpu`) gerade am Leben sind und leitet die Anfragen dorthin um. Er fragt sogar mit `nvidia-smi` tief im Container nach dem Hardware-Namen der Grafikkarte.

> [!tip] Geniales Pattern: Fail-Safe Recovery
> Wenn der User festlegt, dass **Tool_Selector** auf `GPU1` laufen soll, diese GPU aber gerade überhitzt oder der Container gecrasht ist, rettet der `role_endpoint_resolver.py` die Anfrage autonom und schiebt sie fallback-mäßig auf die CPU.

### 3. Chunking Workspace (`workspace.py` & `chunker.py`)
Wenn der User hunderte Seiten Text kopiert (Long Context), reicht der VRAM nicht. 
Der `WorkspaceManager` erstellt unter `/tmp/trion/jarvis/workspace/{conversation_id}/` eine Session mit File-Locking (um Race Conditions bei asynchronen Aufrufen zu verhindern). Der Input wird in die Ordner `chunks/` zerlegt, getrennt durchs LLM verarbeitet und am Ende zu einer aggregierten Meta-Summary zusammengebaut. 

## ⚠️ Architektur-Smells

> [!warning] Zirkuläre Kopplung in Utils
> Der `ollama_endpoint_manager.py` ruft innerhalb der Funktion `_docker_client()` indirekt Code aus dem `container_commander` auf!
> Utils sollten das absolut unterste Fundament (Layer 0) der Architektur sein. Wenn Layer-0-Code plötzlich nach oben ins Layer-3-Domain-Modul (`container_commander`) greift, entsteht eine zirkuläre Abhängigkeit, die den Code schwer testbar macht.
