from core.work_context.contracts import (
    WorkContext,
    WorkContextFact,
    WorkContextSource,
    WorkContextStatus,
    WorkContextUpdate,
)


def test_work_context_normalizes_and_deduplicates_fields():
    ctx = WorkContext(
        conversation_id="  conv-123  ",
        topic="  Python   Entwicklungscontainer   starten  ",
        status=WorkContextStatus.BLOCKED,
        source=WorkContextSource.TASK_LOOP,
        updated_at=" 2026-04-22T18:40:00Z ",
        last_step="  Blueprints   pruefen  ",
        next_step="  Python-Blueprint  auswaehlen ",
        blocker="  request_container:routing_block ",
        verified_facts=(
            WorkContextFact(key="blueprints", value="Python Sandbox gefunden"),
            WorkContextFact(key="blueprints", value="Python Sandbox gefunden"),
        ),
        missing_facts=(" blueprint_id ", " blueprint_id ", "block_reason"),
        capability_context={"request_family": "python_container", "": "drop"},
        metadata={"trace_id": "abc", "": "drop"},
    )

    assert ctx.conversation_id == "conv-123"
    assert ctx.topic == "Python Entwicklungscontainer starten"
    assert ctx.status == WorkContextStatus.BLOCKED
    assert ctx.source == WorkContextSource.TASK_LOOP
    assert ctx.has_blocker is True
    assert ctx.is_open is True
    assert ctx.is_terminal is False
    assert len(ctx.verified_facts) == 1
    assert ctx.missing_facts == ("blueprint_id", "block_reason")
    assert dict(ctx.capability_context) == {"request_family": "python_container"}
    assert dict(ctx.metadata) == {"trace_id": "abc"}


def test_work_context_to_dict_serializes_enums_and_facts():
    ctx = WorkContext(
        conversation_id="conv-1",
        topic="Container-Auswahl",
        status=WorkContextStatus.WAITING,
        source=WorkContextSource.WORKSPACE_EVENTS,
        verified_facts=(
            WorkContextFact(
                key="selected_blueprint",
                value="python-sandbox",
                source=WorkContextSource.TASK_LOOP,
                confidence=0.9,
            ),
        ),
    )

    out = ctx.to_dict()

    assert out["status"] == "waiting"
    assert out["source"] == "workspace_events"
    assert out["verified_facts"][0]["key"] == "selected_blueprint"
    assert out["verified_facts"][0]["source"] == "task_loop"


def test_work_context_update_omits_unset_fields():
    update = WorkContextUpdate(
        next_step=" Blueprints erneut pruefen ",
        missing_facts=("python_blueprint", "python_blueprint"),
        metadata={"origin": "task_loop"},
    )

    out = update.to_dict()

    assert out == {
        "next_step": "Blueprints erneut pruefen",
        "missing_facts": ["python_blueprint"],
        "metadata": {"origin": "task_loop"},
    }


def test_work_context_terminal_status_helpers():
    completed = WorkContext(
        conversation_id="conv-2",
        status=WorkContextStatus.COMPLETED,
    )
    cancelled = WorkContext(
        conversation_id="conv-3",
        status=WorkContextStatus.CANCELLED,
    )

    assert completed.is_terminal is True
    assert completed.is_open is False
    assert cancelled.is_terminal is True
    assert cancelled.is_open is False
