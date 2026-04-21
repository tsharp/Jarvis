from core.task_loop.chat_runtime import (
    build_initial_chat_plan,
    continue_chat_task_loop,
    is_task_loop_candidate,
    maybe_handle_chat_task_loop_turn,
    should_restart_task_loop,
    start_chat_task_loop,
)
from core.task_loop.contracts import (
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
    TERMINAL_STATES,
)
from core.task_loop.store import TaskLoopStore


def test_task_loop_candidate_is_explicit_only():
    assert is_task_loop_candidate("Task-Loop: Bitte mach das schrittweise")
    assert is_task_loop_candidate("Bitte im Multistep Modus einen Plan machen")
    assert is_task_loop_candidate("kurze frage", {"task_loop": True})
    assert not is_task_loop_candidate(
        "Bitte schrittweise einen Plan machen: Pruefe den neuen Multistep Loop"
    )
    assert not is_task_loop_candidate("Bitte mach das schrittweise")
    assert not is_task_loop_candidate("was ist 2+2?")


class TestSemanticToolQueryDetection:
    """Verb × Noun two-part matching triggers task loop for tool-requiring questions."""

    # ── True cases: reported bug + common variants ──────────────────────────

    def test_siehst_du_welche_api_keys(self):
        assert is_task_loop_candidate("siehst du welche api keys du hast?")

    def test_welche_api_keys_hast_du(self):
        assert is_task_loop_candidate("welche api keys hast du?")

    def test_hast_du_secrets(self):
        assert is_task_loop_candidate("hast du secrets gespeichert?")

    def test_kannst_du_mir_die_skills_zeigen(self):
        assert is_task_loop_candidate("kannst du mir die skills zeigen?")

    def test_welche_skills_gibt_es(self):
        assert is_task_loop_candidate("welche skills gibt es?")

    def test_welche_container_laufen(self):
        assert is_task_loop_candidate("welche container laufen gerade?")

    def test_liste_alle_secrets(self):
        assert is_task_loop_candidate("liste alle secrets auf")

    def test_zeig_mir_die_cron_jobs(self):
        assert is_task_loop_candidate("zeig mir die cron jobs")

    def test_welche_blueprints_hast_du(self):
        assert is_task_loop_candidate("welche blueprints hast du?")

    def test_english_do_you_have_api_keys(self):
        assert is_task_loop_candidate("do you have any api keys?")

    def test_english_list_skills(self):
        assert is_task_loop_candidate("list all skills")

    def test_english_what_are_your_secrets(self):
        assert is_task_loop_candidate("what are your secrets?")

    # ── False cases: noun without inspection verb, or unrelated ─────────────

    def test_no_false_positive_pure_question(self):
        assert not is_task_loop_candidate("was ist 2+2?")

    def test_no_false_positive_noun_only(self):
        # "api keys" mentioned but no inspection verb → not a task loop query
        assert not is_task_loop_candidate("ich habe api keys in meiner app")

    def test_no_false_positive_generic_chat(self):
        assert not is_task_loop_candidate("erkläre mir was ein api key ist")

    def test_no_false_positive_verb_without_tool_noun(self):
        assert not is_task_loop_candidate("siehst du das Problem hier?")

    def test_explicit_flag_still_works(self):
        assert is_task_loop_candidate("kurze frage", {"task_loop": True})


def test_build_initial_chat_plan_strips_task_loop_marker_from_objective():
    plan = build_initial_chat_plan(
        "Bitte schrittweise einen Plan machen: Pruefe kurz den neuen Loop"
    )

    assert plan[0] == "Pruefziel festlegen: Pruefe kurz den neuen Loop"


def test_should_restart_task_loop_requires_explicit_new_loop_prompt():
    assert should_restart_task_loop("Task-Loop: Bitte neu starten")
    assert not should_restart_task_loop("weiter")
    assert not should_restart_task_loop("stoppen")


def test_start_chat_task_loop_auto_continues_safe_steps_and_completes():
    store = TaskLoopStore()
    calls = []

    def save_workspace_entry(**kwargs):
        calls.append(kwargs)
        return {"entry_id": f"evt-{len(calls)}"}

    result = start_chat_task_loop(
        "Bitte im Multistep Modus einen Plan machen",
        "conv-loop",
        store=store,
        save_workspace_entry_fn=save_workspace_entry,
    )

    assert result.done_reason == "task_loop_completed"
    assert result.snapshot.state.value == "completed"
    assert result.snapshot.step_index == 4
    assert len(result.snapshot.workspace_event_ids) == len(calls)
    entry_types = [call["entry_type"] for call in calls]
    assert entry_types[:2] == ["task_loop_started", "task_loop_plan_updated"]
    assert entry_types.count("task_loop_step_started") == 4
    assert entry_types.count("task_loop_step_answered") == 4
    assert entry_types.count("task_loop_step_completed") == 4
    assert entry_types.count("task_loop_reflection") == 4
    assert entry_types[-1] == "task_loop_completed"
    assert all(call["source_layer"] == "task_loop" for call in calls)


def test_continue_chat_task_loop_resumes_and_completes_all_remaining_steps():
    # continue_chat_task_loop laeuft den vollen Auto-Loop — nicht nur einen Schritt.
    # Nach einem einzigen "weiter" auf den wartenden Loop laufen alle verbleibenden
    # Schritte durch und der Loop schliesst mit COMPLETED ab.
    store = TaskLoopStore()
    first = start_chat_task_loop(
        "Bitte schrittweise arbeiten",
        "conv-loop",
        store=store,
        auto_continue=False,
    )
    assert first.snapshot.state == TaskLoopState.WAITING_FOR_USER

    result = continue_chat_task_loop(first.snapshot, "weiter", store=store)

    assert result.done_reason == "task_loop_completed"
    assert result.snapshot.state.value == "completed"
    assert result.snapshot.step_index == 4
    assert len(result.snapshot.completed_steps) == 4
    assert "Task-Loop abgeschlossen" in result.content


def test_continue_chat_task_loop_can_cancel_waiting_loop():
    store = TaskLoopStore()
    first = start_chat_task_loop(
        "Bitte step by step arbeiten",
        "conv-loop",
        store=store,
        auto_continue=False,
    )

    result = continue_chat_task_loop(first.snapshot, "stoppen", store=store)

    assert result.done_reason == "task_loop_cancelled"
    assert result.snapshot.state.value == "cancelled"


def test_continue_chat_task_loop_does_not_advance_runtime_waiting_user_tool_step_on_plain_continue():
    store = TaskLoopStore()
    snapshot = TaskLoopSnapshot(
        objective_id="obj-runtime-wait",
        conversation_id="conv-runtime-wait",
        plan_id="plan-runtime-wait",
        state=TaskLoopState.WAITING_FOR_USER,
        current_step_id="step-tool-1",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
        current_step_status=TaskLoopStepStatus.WAITING_FOR_USER,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        current_plan=["Container kontrolliert anfragen"],
        plan_steps=[],
        pending_step="Container kontrolliert anfragen",
        last_step_result={
            "status": TaskLoopStepStatus.WAITING_FOR_USER.value,
            "step_type": TaskLoopStepType.TOOL_REQUEST.value,
            "step_execution_source": TaskLoopStepExecutionSource.ORCHESTRATOR.value,
        },
    )

    result = continue_chat_task_loop(snapshot, "weiter", store=store)

    assert result.done_reason == "task_loop_waiting_for_user"
    assert result.snapshot.state.value == "waiting_for_user"
    assert result.snapshot.pending_step == "Container kontrolliert anfragen"
    assert result.snapshot.step_index == 0
    assert "konkrete Antwort" in result.content


def test_explicit_task_loop_prompt_restarts_waiting_loop_instead_of_repeating_wait_state():
    store = TaskLoopStore()
    waiting = start_chat_task_loop(
        "Task-Loop: Bitte schrittweise arbeiten",
        "conv-loop",
        store=store,
        auto_continue=False,
    )

    result = maybe_handle_chat_task_loop_turn(
        "Task-Loop: Pruefe kurz den neuen Multistep Loop und zeige mir sichere Zwischenstaende",
        "conv-loop",
        store=store,
        thinking_plan={
            "intent": "Multistep Loop pruefen",
            "hallucination_risk": "low",
            "suggested_tools": [],
        },
    )

    assert waiting.done_reason == "task_loop_waiting_for_user"
    assert result is not None
    assert result.done_reason == "task_loop_completed"
    assert result.snapshot.state.value == "completed"
    assert "Der Task-Loop wartet weiter." not in result.content


def test_maybe_handle_chat_task_loop_turn_ignores_normal_question():
    store = TaskLoopStore()

    assert (
        maybe_handle_chat_task_loop_turn(
            "was ist 2+2?",
            "conv-loop",
            store=store,
        )
        is None
    )
