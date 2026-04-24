---
Tags: [TRION, Architektur, Core]
aliases: [Core, /core]
---

# 🧠 Core Grundsystem

> [!info] Zusammenfassung
> Der Core (zu finden im `/core`-Ordner) ist das "zentrale Nervensystem" von TRION. Seine wichtigste Aufgabe ist es, die kognitiven Schritte und den Informationsfluss strikt zu steuern.

Das grundlegende Architektur-Prinzip (die Invariante) des Cores lautet **Single Control Authority**: Richtlinien- und Sicherheitsentscheidungen werden nur an *einer* zentralen Stelle getroffen und die nachgelagerten Systeme führen nur noch aus.

---

## 🏗️ Das neue 4-Layer System

Diese Schichten sind spezialisierte Einheiten (Klassen) innerhalb des Cores:

1. **Layer 0: [[Tool Selector]]**
   - **Was er tut:** Er führt eine reine, pfeilschnelle semantische Suche über Vector-Datenbanken durch, um Tool-Kandidaten zu finden.
   - **Das Besondere:** Er nutzt **kein LLM**, spart also massiv Kosten und Latenz. Er bereitet lediglich die Werkzeuge vor, die für die Anfrage in Frage kommen.
2. **Layer 1: [[Thinking]] (`thinking.py`)**
   - **Was er tut:** Analysiert den Nutzer-Input, erstellt einen strukturierten Plan (`thinking_plan`) und wählt aus den Kandidaten des Tool Selectors die tatsächlich benötigten Tools aus.
3. **Layer 2: [[Control]] (`control.py`)**
   - **Was er tut:** Er ist die "Policy Authority". Hier passiert die finale Prüfung nach Sicherheit, Limits und Rechten. Aus ihm fällt die unabänderliche `ControlDecision` heraus.
4. **Layer 3: [[Output]] (`output.py`)**
   - **Was er tut:** Er sammelt alle Pläne, Freigaben und die Ergebnisse der ausgeführten Tools und formuliert daraus die finale, lesbare Anwort für den User.

> [!note] Ausführungsschicht
> Darunter liegt als reiner „Befehlsempfänger“ noch der [[Tool executor]], welcher als Ausführer von Side-Effekts agiert, selbst aber niemals kognitive Entscheidungen trifft.

---

## ⚙️ Der Orchestrator – Wo gehört er hin?

Der [[Orchestrator]] (`core/orchestrator.py` alias `PipelineOrchestrator`) **ist das Herzstück des Cores und verbindet alles miteinander.**

Ohne ihn wären die Layer nur lose, isolierte Skripte. Er ist die "Pipeline-Maschine", durch welche eine Nutzeranfrage gereicht wird. 

**Sein Job ist es:**
1. Den Request vom Adapter anzunehmen.
2. Den **Tool Selector** den passenden Kontext suchen zu lassen.
3. Die Information an **Thinking** zu reichen und zu warten.
4. Den Plan an **Control** zu reichen.
5. Sofern Control es erlaubt, die Tools ausführen zu lassen.
6. Das Ergebnis gebündelt an den **Output** zu übergeben.

*(In der `core/bridge.py` sieht man sehr schön, dass die "CoreBridge" heutzutage im Grunde nur noch eine Weiterleitung an genau diesen Orchestrator ist).*

---

> [!abstract] Fazit
> - **Der Core** ist die gesamte Pipeline-Logik im `/core`-Ordner. Er separiert Denken von Ausführen.
> - **Die Layer** (Tool Selector, Thinking, Control, Output) sind die "Inseln", auf denen einzelne Schritte passieren.
> - **Der Orchestrator** ist das Fließband, das die Daten sicher und in exakt der richtigen Reihenfolge von Schicht zu Schicht transportiert.