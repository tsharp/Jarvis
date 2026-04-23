from unittest.mock import MagicMock, patch


def _mock_hub_with_events(events):
    hub = MagicMock()
    hub.call_tool.return_value = {"events": events}
    return hub


def test_build_small_model_context_injects_work_context_when_task_loop_events_missing():
    from core.context_manager import ContextManager
    from core.task_loop.contracts import (
        TaskLoopSnapshot,
        TaskLoopState,
        TaskLoopStepExecutionSource,
        TaskLoopStepStatus,
        TaskLoopStepType,
    )

    cm = ContextManager.__new__(ContextManager)
    cm._protocol_cache = {}

    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-ctx",
        plan_id="plan-1",
        state=TaskLoopState.WAITING_FOR_USER,
        current_step_id="step-2",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
        current_step_status=TaskLoopStepStatus.WAITING_FOR_USER,
        step_execution_source=TaskLoopStepExecutionSource.LOOP,
        current_plan=["Ziel klaeren", "Rueckfrage beantworten", "Container starten"],
        completed_steps=["Ziel klaeren"],
        pending_step="Rueckfrage beantworten",
        objective_summary="Container-Auswahl abschliessen",
    )

    mock_hub = _mock_hub_with_events([])
    fake_store = MagicMock()
    fake_store.get.return_value = snapshot

    with patch("mcp.hub.get_hub", return_value=mock_hub), \
         patch("core.typedstate_csv_loader.maybe_load_csv_events", return_value=[]), \
         patch("config.get_typedstate_mode", return_value="off"), \
         patch("config.get_typedstate_csv_enable", return_value=False), \
         patch("core.context_manager.get_task_loop_store", return_value=fake_store):
        result = cm.build_small_model_context(conversation_id="conv-ctx")

    assert "TASK_CONTEXT Container-Auswahl abschliessen state=waiting_for_user pending=Rueckfrage beantworten" in result
    assert "Resume task context: Rueckfrage beantworten" in result


def test_build_small_model_context_does_not_duplicate_when_task_loop_events_exist():
    from core.context_manager import ContextManager

    cm = ContextManager.__new__(ContextManager)
    cm._protocol_cache = {}

    events = [
        {
            "id": "evt-1",
            "event_type": "task_loop_context_updated",
            "created_at": "2026-04-23T02:30:00.000000Z",
            "event_data": {
                "conversation_id": "conv-ctx",
                "background_loop_state": "waiting_for_user",
                "background_loop_topic": "Container-Auswahl abschliessen",
                "background_loop_pending_step": "Rueckfrage beantworten",
            },
        }
    ]
    mock_hub = _mock_hub_with_events(events)
    fake_store = MagicMock()
    fake_store.get.return_value = None

    with patch("mcp.hub.get_hub", return_value=mock_hub), \
         patch("core.typedstate_csv_loader.maybe_load_csv_events", return_value=[]), \
         patch("config.get_typedstate_mode", return_value="off"), \
         patch("config.get_typedstate_csv_enable", return_value=False), \
         patch("core.context_manager.get_task_loop_store", return_value=fake_store):
        result = cm.build_small_model_context(conversation_id="conv-ctx")

    assert result.count("TASK_CONTEXT Container-Auswahl abschliessen") == 1
