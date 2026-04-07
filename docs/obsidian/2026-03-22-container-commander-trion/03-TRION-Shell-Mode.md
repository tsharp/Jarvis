# TRION Shell Mode

## Ausgangspunkt

TRION konnte bereits Container-bezogene Einzelaktionen ausführen, aber nicht in einer laufenden interaktiven Shell arbeiten. Ziel war deshalb ein eigener Commander-Modus statt einer verbogenen Erweiterung des normalen Chats.

## V1

Zuerst wurde `trion <auftrag>` eingeführt:

- TRION sammelt Logs, Stats und einen kleinen Exec-Snapshot
- daraus entsteht eine fokussierte Container-Analyse
- das war bewusst noch kein echter Shell-Takeover

## V2

Danach wurde `trion shell` als separater Modus gebaut:

- User ist an eine laufende Container-Shell attached
- Eingabe in der Input-Bar geht an TRION statt direkt an die PTY
- TRION erzeugt pro Turn den nächsten Shell-Befehl
- der Befehl wird in die laufende Shell geschrieben
- `/exit` beendet nur den TRION-Modus, nicht die Container-Shell

Wichtig:

- das ist kein normaler Chatflow
- das ist kein kompletter Thinking/Control/Output-Lauf pro Shell-Schritt
- es ist ein eigener Shell-Control-Lane neben der normalen Pipeline

## Warum nicht die normale Pipeline pro Schritt

Die normale TRION-Kette ist gut für diskrete Turns, aber schlecht für eine Live-PTY. Würde man `thinking/control/CIM` bei jedem Shell-Schritt voll dazwischen hängen, gäbe es:

- unnötige Latenz
- mehr Fehl- oder Doppelblockaden
- Ownership-Probleme
- schlechtere Nutzbarkeit im Debugging

Deshalb wurde ein leichter Shell-Policy-Ansatz bevorzugt.

## Härtungen im Shellmodus

Es wurden mehrere wichtige Stabilitätsmaßnahmen umgesetzt:

1. Post-action verification
   Nach Aktionen wird auf sichtbaren Zustandswechsel geprüft.

2. Loop guard / dedupe
   Wiederholte oder semantisch gleiche Befehle werden erkannt und gestoppt.

3. Action classification
   TRION unterscheidet zwischen Diagnose, GUI-Interaktion, Prozesssteuerung, Write-Änderung usw.

4. Better stop reasons
   Statt blind weiterzumachen meldet TRION nachvollziehbare Gründe wie `gui_dialog_still_open`.

5. Summary bridge
   Beim `/exit` wird eine strukturierte Session-Zusammenfassung erzeugt, statt den kompletten PTY-Stream als Memory zu speichern.

## Sprachverhalten

TRION antwortet im Shellmodus inzwischen sprachabhängig. Deutsche Eingaben erzeugen deutsche Antworttexte und lokalisierte Statusmeldungen.

## Grenzen des aktuellen Stands

- noch kein autonomer Mehrschritt-Agent
- noch kein serverseitiger dauerhafter Shell-Autopilot
- noch keine tiefe Risk-/Policy-Gate-Integration für jeden Schritt

Die Entscheidung war bewusst:

- erst stabile Mechanik
- dann Mikro-Loops
- echte Autonomie später
