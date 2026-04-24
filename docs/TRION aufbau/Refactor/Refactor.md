---
Tags: [TRION, Refactoring, Architecture]
aliases: [Refactor]
---

# 🛠️ Refactor-Notizen

> [!warning] Architecture Smell: [[Thinking]] vs `intelligence_modules`
> Der `ThinkingLayer` hat aktuell hardcodierte Prompts, die sich thematisch und inhaltlich mit den `intelligence_modules` überschneiden.

Im Orchestrator (`core/orchestrator_modules/context/semantic.py`) gibt es Loader, die sich direkt mit dem [[Layer 1 (Thinking)]] überschneiden. Dort finden sich folgende dynamische Imports:

```python
from intelligence_modules.container_addons.loader import load_container_addon_context
from intelligence_modules.skill_addons.loader import load_skill_addon_context
```

> [!info] Hintergrund
> Es gibt also bereits ein fortgeschrittenes RAG / Procedural Loading (über das *Causal Intelligence Module - CIM*), das dafür da ist, dynamisch zur Laufzeit das Wissen über Container und Skills aus der Datenbank zu ziehen und dem LLM als Kontext einzuspritzen. 
> Das eigentliche Problem ist, dass Layer 1 diesem System aktuell nicht genug vertraut und deshalb hardcodierte Befehle im eigenen Prompt mitführt.
