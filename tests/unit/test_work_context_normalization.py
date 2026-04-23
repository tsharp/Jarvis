from core.work_context.contracts import WorkContextStatus
from core.work_context.normalization import (
    build_terminal_task_loop_missing_facts,
    build_terminal_task_loop_verified_facts,
    build_terminal_task_loop_work_context,
)


def test_build_terminal_task_loop_verified_facts_extracts_selected_and_discovered_blueprints():
    facts = build_terminal_task_loop_verified_facts(
        selected_blueprint={"blueprint_id": "python-sandbox", "label": "Python Sandbox"},
        discovered_blueprints=[
            {"id": "python-sandbox", "name": "Python Sandbox"},
            {"id": "db-sandbox", "name": "Database Sandbox"},
        ],
    )

    assert any(item.key == "selected_blueprint" and item.value == "Python Sandbox" for item in facts)
    assert any(item.key == "discovered_blueprints" and "Python Sandbox" in item.value for item in facts)


def test_build_terminal_task_loop_missing_facts_marks_python_and_block_reason():
    missing = build_terminal_task_loop_missing_facts(
        capability_context={"request_family": "python_container"},
        selected_blueprint={},
        discovered_blueprints=[{"id": "db-sandbox", "name": "Database Sandbox"}],
        blocker="request_container:no_jit_match",
    )

    assert missing == ("python_blueprint", "block_reason")


def test_build_terminal_task_loop_work_context_builds_blocked_terminal_context():
    context = build_terminal_task_loop_work_context(
        conversation_id="conv-1",
        topic="Python-Entwicklungscontainer starten",
        source_state="completed",
        next_step="Verfuegbare Blueprints oder Container-Basis pruefen",
        blocker="request_container:no_jit_match",
        capability_context={"request_family": "python_container"},
        selected_blueprint={},
        discovered_blueprints=[{"id": "python-sandbox", "name": "Python Sandbox"}],
        next_tools=["blueprint_list"],
    )

    assert context.conversation_id == "conv-1"
    assert context.status == WorkContextStatus.BLOCKED
    assert context.next_step == "Verfuegbare Blueprints oder Container-Basis pruefen"
    assert context.blocker == "request_container:no_jit_match"
    assert dict(context.metadata)["source_state"] == "completed"
    assert "selected_blueprint" in context.missing_facts
