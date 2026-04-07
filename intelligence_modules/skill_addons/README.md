# Skill Addons

Skill Addons sind kleine semantische Wissensdokumente fuer Skill-Fragen in
TRION.

Ziel:
- Begriffe und Kategorien rund um `Skills` stabilisieren
- offene Skill-Fragen semantisch einordnen
- Antwortregeln gegen Drift explizit machen
- kleine Modelle nicht mit langen Skill-Erklaerungen im Core-Prompt belasten

Wichtig:
- Das ist **keine zweite Truth-Source** fuer konkrete Skill-Inventare.
- Live-Fakten zu installierten Skills, Drafts oder Counts bleiben bei Registry,
  `/v1/skills`, `list_skills` und TypedState.
- Skill Addons liefern nur Begriffe, Grenzen und Antwortregeln.

Empfohlene Struktur:

```text
intelligence_modules/skill_addons/
  README.md
  ADDON_SPEC.md
  taxonomy/
    00-overview.md
    10-runtime-skills.md
    20-drafts.md
    30-tools-vs-skills.md
    40-session-skills.md
    50-answering-rules.md
```

Geplante spaetere Nutzung:
- Thinking erkennt Skill-Fragetypen wie `skill_catalog_context`
- ein Loader waehlt 1-3 passende semantische Leitplanken aus
- Orchestrator kombiniert diese Leitplanken mit einem Live-Runtime-Snapshot
- Output antwortet damit gleichzeitig faktisch und begrifflich sauber

Fuer neue Skill Addons zuerst `ADDON_SPEC.md` lesen.
