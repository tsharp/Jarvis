---
Tags: [TRION, Architecture, Memory, RAG, SQLite]
aliases: [Memory System, sql-memory, vector_store.py]
---

# 🧠 Memory System (`sql-memory`)

Das Memory-System von TRION (unter `/sql-memory/`) bildet das Langzeitgedächtnis der KI. Das Besondere: Es ist nicht direkt in TRION hart verdrahtet, sondern läuft als eigener **FastMCP Server**. TRION steuert sein Gedächtnis also komplett über standardisierte MCP-Tools.

## 🏗️ 1. Architektur & Konzepte

Das System verschmilzt drei Datenbank-Konzepte in einer einzigen SQLite-Datenbank:

1. **Chronologisches Gedächtnis (`memory_save`)**: Einfaches Protokollieren von Nutzer/System-Texten in verschiedene Schichten (`stm` - Short Term, `mtm` - Mid Term, `ltm` - Long Term).
2. **Semantisches Gedächtnis (`vector_store.py`)**: Nutzt das lokale Ollama-Modell (z.B. `mxbai-embed-large-v1:f16`), um Vektoren aus jedem Gedankengang zu berechnen.
3. **Graph-Gedächtnis (`graph/`)**: Fakten ("Danny mag Pizza") werden als strukturierte Knoten (`memory_fact_save`) gespeichert. Mit `memory_graph_search` kann die KI entlang dieses Graphen "wandern" (Graph-Walk), um verbundene Ideen zu finden.

## 🤖 2. Die AI-Wartung (`maintenance_run`)
Bemerkenswert: Das System hat einen KI-gestützten Wartungsmodus. Das Tool `maintenance_run` beauftragt einen Hintergrund-Agenten, die Datenbank aufzuräumen (Knoten mergen, Duplikate löschen, "Ghost"-Einträge markieren).

---

## ⚠️ 3. Identify Technical Debt: Die Python-Vektor-Suche

Hier liegt ein massiver Architektur-Engpass (Performance Bottleneck) versteckt:

> [!warning] Architecture Smell: Brute-Force Vector Search
> In `vector_store.py:search()` wird keine echtes Vektor-Datenbank-Plugin für SQLite (wie `sqlite-vss` oder `sqlite-vec`) verwendet. 
> 
> **Was das System aktuell macht:**
> 1. Es lädt **alle** Embeddings der Konversation per `SELECT * FROM embeddings`.
> 2. Danach iteriert es in Python über diese tausenden Zeilen (!).
> 3. Es entpackt für jede Zeile den JSON-Vektor.
> 4. Es berechnet in Python iterativ die `cosine_similarity`.
> 5. Es sortiert die Ergebnisse dann langsam in einer Liste.
> 
> Das ist für Prototypen in Ordnung (O(N) Laufzeit), aber sobald TRION langes Gedächtnis aufbaut (z.B. 10.000 Einträge), wird diese Python-Schleife die CPU grillen und das RAG-System massiv verlangsamen.

## 🛠️ 4. Refactoring-Plan

1. **SQLite Vector Extension:** Wir müssen schauen, ob wir das sqlite `vss` oder neuerdings `vec` Modul installieren können. Dann läuft die Vektorsuche in Microsekunden auf der C-Ebene statt in einer fehleranfälligen Python JSON-Schleife.
2. **Entkopplung Graph/Vektor:** Die `memory_graph_search` vermischt extrem viele harte Logik-Abfragen (String-Matching für Seed Nodes). Das könnte man über saubere SQL-Joins deutlich beschleunigen.
