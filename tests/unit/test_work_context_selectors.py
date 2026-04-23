from core.work_context.contracts import WorkContext, WorkContextSource, WorkContextStatus
from core.work_context.selectors import (
    has_open_work_context,
    should_execute_from_work_context,
    should_explain_from_work_context,
    visible_next_step,
)


def test_has_open_work_context_true_for_waiting_runtime_context():
    ctx = WorkContext(
        conversation_id="conv-1",
        topic="Container-Auswahl abschliessen",
        status=WorkContextStatus.WAITING,
        source=WorkContextSource.TASK_LOOP,
        next_step="Rueckfrage beantworten",
    )

    assert has_open_work_context(ctx) is True


def test_has_open_work_context_true_for_terminal_unresolved_context():
    ctx = WorkContext(
        conversation_id="conv-1",
        topic="Python-Entwicklungscontainer starten",
        status=WorkContextStatus.COMPLETED,
        source=WorkContextSource.TASK_LOOP,
        blocker="request_container:no_jit_match",
        next_step="Verfuegbare Blueprints oder Container-Basis pruefen",
        missing_facts=("selected_blueprint",),
    )

    assert has_open_work_context(ctx) is True


def test_has_open_work_context_false_for_clean_terminal_context():
    ctx = WorkContext(
        conversation_id="conv-1",
        topic="Python-Entwicklungscontainer starten",
        status=WorkContextStatus.COMPLETED,
        source=WorkContextSource.TASK_LOOP,
    )

    assert has_open_work_context(ctx) is False


def test_visible_next_step_prefers_explicit_next_step():
    ctx = WorkContext(
        conversation_id="conv-1",
        status=WorkContextStatus.BLOCKED,
        next_step="Blueprints pruefen",
        blocker="request_container:no_jit_match",
    )

    assert visible_next_step(ctx) == "Blueprints pruefen"


def test_visible_next_step_falls_back_to_blocker_or_missing_facts():
    blocked = WorkContext(
        conversation_id="conv-1",
        status=WorkContextStatus.COMPLETED,
        blocker="request_container:no_jit_match",
    )
    missing = WorkContext(
        conversation_id="conv-1",
        status=WorkContextStatus.COMPLETED,
        missing_facts=("selected_blueprint",),
    )

    assert visible_next_step(blocked) == "Offenen technischen Blocker pruefen"
    assert visible_next_step(missing) == "Fehlende Fakten klaeren"


def test_should_explain_from_work_context_matches_explanatory_followup():
    ctx = WorkContext(
        conversation_id="conv-1",
        topic="Python-Entwicklungscontainer starten",
        status=WorkContextStatus.COMPLETED,
        blocker="request_container:no_jit_match",
        next_step="Blueprints pruefen",
    )

    assert should_explain_from_work_context("was fehlt noch?", ctx) is True
    assert should_explain_from_work_context("mach weiter", ctx) is False


def test_should_execute_from_work_context_matches_actionable_followup():
    ctx = WorkContext(
        conversation_id="conv-1",
        topic="Python-Entwicklungscontainer starten",
        status=WorkContextStatus.COMPLETED,
        blocker="request_container:no_jit_match",
        next_step="Blueprints pruefen",
    )

    assert should_execute_from_work_context("pruef die Blueprints jetzt", ctx) is True
    assert should_execute_from_work_context("was fehlt noch?", ctx) is False
    assert should_execute_from_work_context("pruef die Blueprints jetzt", None) is False
