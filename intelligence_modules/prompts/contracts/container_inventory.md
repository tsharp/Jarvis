---
scope: container_contract
target: output_layer
query_class: container_inventory
variables: ["required_tools_line", "truth_mode_line"]
status: active
---

### CONTAINER-ANTWORTMODUS:
Containerantworten muessen Runtime-Inventar, Blueprint-Katalog und Session-Binding sichtbar getrennt halten.
Blueprint-Katalog, Runtime-Inventar und Binding niemals unmarkiert in denselben Antworttopf werfen.
Statische Profile oder Taxonomie duerfen erklaeren, aber keine Live-Bindung oder Runtime-Fakten erfinden.
{required_tools_line}
{truth_mode_line}
Bevorzugte Reihenfolge: `Laufende Container`, dann `Gestoppte Container`, dann `Einordnung`.
Im Abschnitt `Laufende Container` nur aktuell laufende Container aus Runtime-Inventar nennen.
Im Abschnitt `Gestoppte Container` nur verifizierte installierte, aber nicht laufende Container nennen.
Keine Blueprints, keine Startempfehlungen und keine Capability-Liste als Hauptantwort einmischen.
Keine ungefragten Betriebsdiagnosen, keine Fehlerursachen und keine Zeitinterpretationen aus Exit-Status ableiten.
Wenn kein laufender oder gestoppter Container verifiziert ist, das explizit als Runtime-Befund sagen statt zu raten.
Blueprints nur in einem explizit markierten Zusatzblock `Verfuegbare Blueprints` nennen, wenn der User diese Ebene ausdruecklich mitfragt und dafuer belegte Blueprint-Evidence vorliegt.
Nutze klare Abschnittsueberschriften wie `Laufende Container`, `Gestoppte Container` und `Einordnung`, wenn sie zur Frage passen; vermeide starre Satzanfangsformeln, wenn eine natuerlichere Antwort gleich klar bleibt.

### EMPFOHLENE ANTWORTSTRUKTUR:
- Laufende Container: verifizierter Runtime-Befund zu aktuell laufenden Containern oder explizit keine verifizierten Treffer.
- Gestoppte Container: verifizierter Runtime-Befund zu installierten, aber nicht laufenden Containern oder explizit keine verifizierten Treffer.
- Einordnung: klare Trennung zwischen Runtime-Inventar und Blueprint-Katalog.
