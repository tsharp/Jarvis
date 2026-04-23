from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from core.layers.control import ControlLayer


@dataclass(frozen=True)
class ControlTaskLoopCase:
    case_id: str
    category: str
    user_text: str
    thinking_plan: dict[str, Any]
    verification: dict[str, Any]
    expected_turn_mode: str
    expected_execution_mode: str
    human_should_task_loop: bool


def _allow_verification(**overrides: Any) -> dict[str, Any]:
    base = {
        "approved": True,
        "decision_class": "allow",
        "corrections": {},
        "warnings": [],
        "final_instruction": "",
    }
    base.update(overrides)
    return base


def _make_case(
    *,
    case_id: str,
    category: str,
    user_text: str,
    thinking_plan: dict[str, Any],
    expected_turn_mode: str,
    expected_execution_mode: str,
    human_should_task_loop: bool,
    verification: dict[str, Any] | None = None,
) -> ControlTaskLoopCase:
    return ControlTaskLoopCase(
        case_id=case_id,
        category=category,
        user_text=user_text,
        thinking_plan=dict(thinking_plan),
        verification=dict(verification or _allow_verification()),
        expected_turn_mode=expected_turn_mode,
        expected_execution_mode=expected_execution_mode,
        human_should_task_loop=human_should_task_loop,
    )


def _build_cases() -> list[ControlTaskLoopCase]:
    cases: list[ControlTaskLoopCase] = []

    explicit_prompts = [
        "Pruef erst die Blueprints, waehle dann den passenden Python-Container und starte ihn.",
        "Analysiere zuerst die Logs, plane dann den Fix und fuehre ihn danach aus.",
        "Gehe Schritt fuer Schritt durch die Datenbankmigration und stoppe bei Konflikten.",
        "Vergleiche die Branches, formuliere den Merge-Plan und fuehre ihn dann aus.",
        "Pruef die freien Ports, entscheide dich fuer einen und starte danach den Service.",
        "Sammle erst die Containerdaten, waehle die beste Runtime und deploye dann.",
        "Schau dir zuerst die Blueprints an, entscheide dich fuer Python und starte danach.",
        "Arbeite das Ticket in mehreren Schritten ab und zeig mir sichtbaren Fortschritt.",
        "Fuehre erst den Sicherheitscheck aus, dann die Konfiguration und dann den Start.",
        "Plane den Container-Rollout, bestaetige die Auswahl und setze ihn anschliessend um.",
        "Pruef zuerst welche Images passen, waehle eines und erstelle dann den Container.",
        "Mach daraus bitte einen sichtbaren Ablauf mit Zwischenstatus und Ausfuehrung.",
        "Fuehre nacheinander Discovery, Auswahl und Start fuer den Python-Container aus.",
        "Starte einen Arbeitsloop: pruefen, entscheiden, ausfuehren und rueckmelden.",
        "Bearbeite das Thema als mehrstufigen Ablauf statt als Einmalantwort.",
        "Arbeite die Anfrage in mehreren Schritten ab und zeige den Fortschritt an.",
        "Bitte als Task-Loop: erst Bestand pruefen, dann Auswahl, dann Aktion.",
        "Nimm das als orchestrierten Mehrschritt-Task und fuehre ihn bis zum Ende aus.",
        "Plane erst die Schritte fuer den Container und arbeite sie dann sichtbar ab.",
        "Fuehre den Auftrag als Task-Loop mit Pruefung, Auswahl und Start durch.",
    ]
    for idx, prompt in enumerate(explicit_prompts, start=1):
        cases.append(
            _make_case(
                case_id=f"explicit-{idx:02d}",
                category="explicit_task_loop_request",
                user_text=prompt,
                thinking_plan={
                    "task_loop_candidate": True,
                    "_task_loop_explicit_signal": True,
                    "needs_visible_progress": bool(idx % 2),
                    "sequential_complexity": 4 + (idx % 4),
                },
                expected_turn_mode="task_loop",
                expected_execution_mode="task_loop",
                human_should_task_loop=True,
            )
        )

    visible_progress_prompts = [
        "Container-Anfrage mit sichtbaren Zwischenschritten bearbeiten.",
        "Bitte mit Fortschrittsanzeige pruefen, auswaehlen und starten.",
        "Mach daraus einen Ablauf mit Statusupdates fuer jeden Schritt.",
        "Arbeite die Anfrage mit sichtbarem Fortschritt ab.",
        "Ich will die Zwischenschritte bei der Container-Auswahl sehen.",
        "Fuehre die Runtime-Suche mit Fortschritt und Rueckmeldung aus.",
        "Zeig jeden Schritt, waehrend du den passenden Blueprint ermittelst.",
        "Bitte iterativ und sichtbar durch die Container-Erstellung gehen.",
        "Nicht nur antworten, sondern den Vorgang mit Statusanzeigen abarbeiten.",
        "Zeig mir den Ablauf von Discovery bis Start als sichtbaren Prozess.",
        "Arbeite den Python-Container-Auftrag mit Fortschrittsanzeige ab.",
        "Bitte den mehrstufigen Start mit sichtbarem Plan ausfuehren.",
        "Geh transparent durch Analyse, Auswahl und Start.",
        "Mit klaren Zwischenstatus den passenden Container vorbereiten.",
        "Fuer den Container bitte sichtbaren Fortschritt verwenden.",
    ]
    for idx, prompt in enumerate(visible_progress_prompts, start=1):
        cases.append(
            _make_case(
                case_id=f"progress-{idx:02d}",
                category="visible_progress_multistep",
                user_text=prompt,
                thinking_plan={
                    "task_loop_candidate": True,
                    "needs_visible_progress": True,
                    "sequential_complexity": 2 + (idx % 5),
                },
                expected_turn_mode="task_loop",
                expected_execution_mode="task_loop",
                human_should_task_loop=True,
            )
        )

    hidden_complexity_prompts = [
        "Container vorbereiten, Konfiguration ableiten und Deployment sicher abschliessen.",
        "Migration pruefen, Risiken bewerten, Reihenfolge festlegen und ausfuehren.",
        "Die komplette Python-Sandbox von Blueprint bis Start aufsetzen.",
        "Abhaengigkeiten klaeren, Umgebung waehlen und danach produktiv starten.",
        "Logs auswerten, Ursache isolieren, Fix planen und ausrollen.",
        "Runtime analysieren, Parameter setzen, dann den Container bereitstellen.",
        "Eine neue Dev-Umgebung aufbauen und alle notwendigen Teilschritte abarbeiten.",
        "Das Deployment inklusive Pruefung, Auswahl und Ausfuehrung sauber durchziehen.",
        "Build, Verifikation, Konfiguration und Start in einer Kette erledigen.",
        "Analyse, Vorbereitung und Umsetzung fuer den Container in einem Lauf erledigen.",
        "Systemzustand pruefen, den passenden Pfad auswaehlen und umsetzen.",
        "Das Problem mit mehreren abhaengigen Schritten bis zur Fertigstellung loesen.",
        "Von der Blueprint-Pruefung bis zum Container-Start alles nacheinander erledigen.",
        "Mehrere technische Vorbedingungen klaeren und danach die Runtime starten.",
        "Die Python-Container-Anfrage vollstaendig und sequentiell ausfuehren.",
    ]
    for idx, prompt in enumerate(hidden_complexity_prompts, start=1):
        cases.append(
            _make_case(
                case_id=f"complex-{idx:02d}",
                category="implicit_high_complexity",
                user_text=prompt,
                thinking_plan={
                    "task_loop_candidate": True,
                    "needs_visible_progress": False,
                    "sequential_complexity": 7 + (idx % 4),
                },
                expected_turn_mode="task_loop",
                expected_execution_mode="task_loop",
                human_should_task_loop=True,
            )
        )

    active_loop_prompts = [
        "Weiter.",
        "Mach weiter.",
        "Setz den offenen Ablauf fort.",
        "Bitte den letzten Schritt fortsetzen.",
        "Weiter mit dem Container-Thema.",
        "Nimm den offenen Task wieder auf.",
        "Fortsetzen und den naechsten Schritt ausfuehren.",
        "Mach im laufenden Ablauf weiter.",
        "Bitte den pausierten Task fortfuehren.",
        "Weiter mit der Container-Auswahl.",
    ]
    for idx, prompt in enumerate(active_loop_prompts, start=1):
        cases.append(
            _make_case(
                case_id=f"active-{idx:02d}",
                category="active_task_loop_presence",
                user_text=prompt,
                thinking_plan={
                    "_task_loop_active": True,
                    "_task_loop_active_state": "waiting_for_user",
                    "task_loop_candidate": False,
                    "needs_visible_progress": False,
                    "sequential_complexity": 1,
                },
                expected_turn_mode="task_loop",
                expected_execution_mode="task_loop",
                human_should_task_loop=True,
            )
        )

    under_signaled_prompts = [
        "Ich brauche einen Python-Container mit passender Auswahl und Start.",
        "Finde fuer mich die richtige Runtime und starte sie dann.",
        "Richte die Entwicklungsumgebung ein und nimm die beste Option.",
        "Mach die neue Container-Umgebung bitte fertig.",
        "Setz das Deployment so auf, dass es danach direkt laeuft.",
        "Stell mir die passende Python-Sandbox bereit.",
        "Bereite den Container vor und bring ihn an den Start.",
        "Konfiguriere die Umgebung und fuehre sie anschliessend aus.",
        "Suche das Richtige aus und starte es dann bitte.",
        "Ich will die Umgebung einsatzbereit haben.",
        "Bitte die neue Sandbox komplett aufsetzen.",
        "Nimm die beste Option und mach sie startklar.",
        "Mach daraus eine nutzbare Python-Entwicklungsumgebung.",
        "Bring die Container-Anfrage bis zum Start zum Abschluss.",
        "Ich brauche eine laufende Python-Umgebung aus dem Bestand.",
    ]
    for idx, prompt in enumerate(under_signaled_prompts, start=1):
        if idx <= 8:
            thinking_plan = {
                "task_loop_candidate": True,
                "needs_visible_progress": False,
                "sequential_complexity": 4 + (idx % 2),
                "resolution_strategy": "container_request",
                "_container_capability_context": {
                    "request_family": "python_container",
                    "known_fields": {},
                },
            }
        else:
            thinking_plan = {
                "task_loop_candidate": False,
                "needs_visible_progress": False,
                "sequential_complexity": 4,
                "resolution_strategy": "container_request",
                "_container_capability_context": {
                    "request_family": "python_container",
                    "known_fields": {},
                },
            }
        cases.append(
            _make_case(
                case_id=f"undersignaled-{idx:02d}",
                category="human_multistep_but_under_signaled",
                user_text=prompt,
                thinking_plan=thinking_plan,
                expected_turn_mode="task_loop",
                expected_execution_mode="task_loop",
                human_should_task_loop=True,
            )
        )

    single_turn_prompts = [
        "Wie viel RAM ist aktuell frei?",
        "Welcher Container laeuft gerade?",
        "Welche Blueprints gibt es?",
        "Wie lautet die Python-Version im Host?",
        "Zeig mir die letzten Logs.",
        "Ist Port 8000 frei?",
        "Welche Datenbank laeuft aktuell?",
        "Wie viele Container sind aktiv?",
        "Welcher Branch ist ausgecheckt?",
        "Welche CPU-Last habe ich gerade?",
        "Wie heisst der aktive Blueprint?",
        "Ist der Service healthy?",
        "Welche Umgebungsvariable ist gesetzt?",
        "Wie gross ist das Projektverzeichnis?",
        "Welche Container-Images sind lokal verfuegbar?",
    ]
    for idx, prompt in enumerate(single_turn_prompts, start=1):
        cases.append(
            _make_case(
                case_id=f"single-{idx:02d}",
                category="clear_single_turn",
                user_text=prompt,
                thinking_plan={
                    "task_loop_candidate": False,
                    "needs_visible_progress": False,
                    "sequential_complexity": 1 + (idx % 3),
                    "is_fact_query": True,
                },
                expected_turn_mode="single_turn",
                expected_execution_mode="direct",
                human_should_task_loop=False,
            )
        )

    interactive_prompts = [
        "Soll ich das Paket wirklich installieren?",
        "Willst du, dass ich die Aenderung jetzt anwende?",
        "Brauchst du vor dem Start noch eine Bestaetigung?",
        "Darf ich den Container mit diesen Rechten anlegen?",
        "Soll die Installation jetzt wirklich losgehen?",
        "Moechtest du den riskanten Schritt wirklich ausfuehren?",
        "Bitte entscheide, ob ich das Skill nachinstallieren soll.",
        "Soll ich die Konfiguration jetzt verbindlich uebernehmen?",
        "Ich brauche deine Freigabe fuer den naechsten Schritt.",
        "Willst du diese potenziell riskante Aktion bestaetigen?",
    ]
    for idx, prompt in enumerate(interactive_prompts, start=1):
        verification = _allow_verification(_needs_skill_confirmation=True)
        if idx % 2 == 0:
            verification = _allow_verification()
            thinking_plan = {
                "task_loop_candidate": False,
                "needs_visible_progress": False,
                "sequential_complexity": 2,
                "_pending_intent": "install_skill",
            }
        else:
            thinking_plan = {
                "task_loop_candidate": False,
                "needs_visible_progress": False,
                "sequential_complexity": 2,
            }
        cases.append(
            _make_case(
                case_id=f"interactive-{idx:02d}",
                category="interactive_defer_confirmation",
                user_text=prompt,
                thinking_plan=thinking_plan,
                verification=verification,
                expected_turn_mode="interactive_defer",
                expected_execution_mode="interactive_defer",
                human_should_task_loop=False,
            )
        )

    assert len(cases) == 100, f"Expected 100 benchmark cases, got {len(cases)}"
    return cases


CASES = _build_cases()


@pytest.fixture(scope="module")
def control_layer() -> ControlLayer:
    return ControlLayer()


def _evaluate_case(layer: ControlLayer, case: ControlTaskLoopCase) -> dict[str, Any]:
    corrected = layer.apply_corrections(
        case.thinking_plan,
        case.verification,
        user_text=case.user_text,
    )
    return {
        "case_id": case.case_id,
        "category": case.category,
        "user_text": case.user_text,
        "expected_turn_mode": case.expected_turn_mode,
        "actual_turn_mode": corrected.get("_authoritative_turn_mode"),
        "expected_execution_mode": case.expected_execution_mode,
        "actual_execution_mode": corrected.get("_authoritative_execution_mode"),
        "human_should_task_loop": case.human_should_task_loop,
        "actual_task_loop": corrected.get("_authoritative_turn_mode") == "task_loop",
        "reason": corrected.get("_authoritative_turn_mode_reason"),
    }


def _build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    contract_hits = sum(
        1
        for row in results
        if row["expected_turn_mode"] == row["actual_turn_mode"]
        and row["expected_execution_mode"] == row["actual_execution_mode"]
    )
    human_positive = sum(1 for row in results if row["human_should_task_loop"])
    predicted_positive = sum(1 for row in results if row["actual_task_loop"])
    true_positive = sum(1 for row in results if row["human_should_task_loop"] and row["actual_task_loop"])
    false_negative = sum(1 for row in results if row["human_should_task_loop"] and not row["actual_task_loop"])
    false_positive = sum(1 for row in results if not row["human_should_task_loop"] and row["actual_task_loop"])
    true_negative = sum(1 for row in results if not row["human_should_task_loop"] and not row["actual_task_loop"])

    def _pct(num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return round((num / den) * 100.0, 2)

    categories: dict[str, dict[str, Any]] = {}
    for row in results:
        bucket = categories.setdefault(
            row["category"],
            {"total": 0, "contract_hits": 0, "human_positive": 0, "actual_positive": 0},
        )
        bucket["total"] += 1
        if row["expected_turn_mode"] == row["actual_turn_mode"] and row["expected_execution_mode"] == row["actual_execution_mode"]:
            bucket["contract_hits"] += 1
        if row["human_should_task_loop"]:
            bucket["human_positive"] += 1
        if row["actual_task_loop"]:
            bucket["actual_positive"] += 1

    for bucket in categories.values():
        bucket["contract_accuracy_pct"] = _pct(bucket["contract_hits"], bucket["total"])
        bucket["task_loop_prediction_pct"] = _pct(bucket["actual_positive"], bucket["total"])
        bucket["human_task_loop_rate_pct"] = _pct(bucket["human_positive"], bucket["total"])

    return {
        "total": total,
        "contract_hits": contract_hits,
        "contract_accuracy_pct": _pct(contract_hits, total),
        "human_task_loop_cases": human_positive,
        "predicted_task_loop_cases": predicted_positive,
        "true_positive": true_positive,
        "false_negative": false_negative,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "human_task_loop_recall_pct": _pct(true_positive, human_positive),
        "human_task_loop_precision_pct": _pct(true_positive, predicted_positive),
        "human_task_loop_accuracy_pct": _pct(true_positive + true_negative, total),
        "categories": categories,
    }


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.case_id)
def test_control_task_loop_detection_contract_case(control_layer: ControlLayer, case: ControlTaskLoopCase):
    result = _evaluate_case(control_layer, case)

    assert result["actual_execution_mode"] == case.expected_execution_mode, (
        f"{case.case_id} ({case.category}) execution_mode mismatch for "
        f"{case.user_text!r}: expected {case.expected_execution_mode}, "
        f"got {result['actual_execution_mode']} (reason={result['reason']})"
    )
    assert result["actual_turn_mode"] == case.expected_turn_mode, (
        f"{case.case_id} ({case.category}) turn_mode mismatch for "
        f"{case.user_text!r}: expected {case.expected_turn_mode}, "
        f"got {result['actual_turn_mode']} (reason={result['reason']})"
    )


def test_control_task_loop_detection_benchmark_report(control_layer: ControlLayer):
    results = [_evaluate_case(control_layer, case) for case in CASES]
    report = _build_report(results)

    print("\n[Control Task-Loop Benchmark]")
    print(f"cases={report['total']}")
    print(
        "contract_accuracy="
        f"{report['contract_hits']}/{report['total']} ({report['contract_accuracy_pct']}%)"
    )
    print(
        "human_task_loop_recall="
        f"{report['true_positive']}/{report['human_task_loop_cases']} "
        f"({report['human_task_loop_recall_pct']}%)"
    )
    print(
        "human_task_loop_precision="
        f"{report['true_positive']}/{report['predicted_task_loop_cases']} "
        f"({report['human_task_loop_precision_pct']}%)"
    )
    print(
        "human_task_loop_accuracy="
        f"{report['true_positive'] + report['true_negative']}/{report['total']} "
        f"({report['human_task_loop_accuracy_pct']}%)"
    )
    print("categories:")
    for category in sorted(report["categories"].keys()):
        bucket = report["categories"][category]
        print(
            f"  - {category}: total={bucket['total']} "
            f"contract={bucket['contract_accuracy_pct']}% "
            f"human_loop_rate={bucket['human_task_loop_rate_pct']}% "
            f"predicted_loop_rate={bucket['task_loop_prediction_pct']}%"
        )

    assert report["total"] == 100
    assert report["contract_accuracy_pct"] >= 99.0
    assert report["human_task_loop_recall_pct"] >= 95.0
    assert report["human_task_loop_precision_pct"] >= 95.0
