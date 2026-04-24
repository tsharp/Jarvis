---
Tags: [TRION, Architecture, Persona, Prompt]
aliases: [Persona System, persona.py]
---

# 🎭 Persona & Context (Die KI-Psychologie)

Die Verzeichnisse `/personas/` und die Datei `core/persona.py` bilden die "Persönlichkeit" von TRION. Hier entscheidet sich, mit welchem Basis-Charakter (System-Prompt) das LLM gefüttert wird, bevor es auf die erste User-Nachricht antwortet.

## 🏗️ 1. Die Architektur der Persona

TRION nutzt keine statischen System-Prompts, sondern baut sich bei jeder Anfrage dynamisch einen neuen Prompt zusammen (`build_system_prompt`):

1. **Text-Dateien (`personas/*.txt`):** Hier liegen einfache Textdateien (z.B. `default.txt`, `dev_mode.txt`), in denen in Blöcken wie `[PERSONALITY]` oder `[RULES]` die Spielregeln fixiert sind.
2. **Der Formwandler:** Sobald TRION checkt, welcher User spricht, holt er sich das Profil ("Ist der User Programmierer oder Künstler?") aus dem `sql-memory` und schiebt es in die Persona. Die KI mutiert also dynamisch und ändert ihren Schreibstil.
3. **Hardware-Bewusstsein:** TRION bekommt hart in die Persona gehämmert, dass die Hardware (RAM, VRAM) seine "physischen Grenzen" sind. Die Persona zwingt die KI, Container-Skripte abzubrechen, wenn ihr eigener VRAM leerläuft.

## ⚠️ 2. Identify Technical Debt: Hardcoding und Parser

Hier haben wir tief in der Architektur zwei gewaltige "Smells" (Anti-Patterns) entdeckt:

> [!warning] Architecture Smell 1: Der handgeschriebene Text-Parser
> In `core/persona.py` gibt es eine gigantische Funktion `parse_persona_txt()`, die versucht, die `.txt` Dateien händisch Zeile für Zeile auszulesen (`if line.startswith('[')`). 
> Wenn man in Zukunft eine neue Option wie `[BEHAVIOR]` hinzufügen will, wird sie schlichtweg ignoriert, solange nicht extra Python-Logik in den Parser programmiert wird (Verletzung des *Open-Closed-Prinzips*).

> [!warning] Architecture Smell 2: Prompts tief im Python Code
> In der `build_system_prompt()` Funktion werden nicht nur die Texte aus den `.txt` Dateien geladen, sondern es werden hart in Python (String Concatenation) spezifische Prompts für den `container-commander` und `trion-home` generiert! 
> 
> *Beispiel im Code:* `parts.append("Starte nur Container die du wirklich brauchst.")`
>
> Hier bricht das System hart die Schichten (Layer Violation): Die Basis-Persona-Logik weiß, dass es einen `container-commander` gibt.

## 🛠️ 3. Refactoring-Plan

1. **Standardisierte Formate:** Weg vom Custom `.txt` Parsing. Die Personas sollten als **YAML** oder JSON-Dateien gespeichert werden. Python kann diese in einem 3-Zeiler lesen (Pydantic-Modelle), womit hunderte Zeilen Parsing-Code überflüssig werden.
2. **Prompt-Templates:** Statt Sätze im Code mit `parts.append()` aneinanderzureihen, sollte Jinja2 oder ein ähnliches Template-System genutzt werden.
3. **Entkopplung:** Die Container-Regeln dürfen nicht im Basis-System-Prompt (Persona) hardkodiert sein. Sie sollten als Metadaten vom MCP-Hub geschickt werden, wenn Tools vom System registriert werden!
