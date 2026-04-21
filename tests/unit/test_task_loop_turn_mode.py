from core.layers.control import ControlLayer


def test_apply_corrections_sets_authoritative_task_loop_turn_mode_for_candidate():
    layer = ControlLayer()

    corrected = layer.apply_corrections(
        {
            "task_loop_candidate": True,
            "needs_visible_progress": True,
            "sequential_complexity": 8,
        },
        {
            "approved": True,
            "decision_class": "allow",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
        },
    )

    assert corrected["_authoritative_execution_mode"] == "task_loop"
    assert corrected["execution_mode"] == "task_loop"
    assert "needs_visible_progress" in corrected["_authoritative_execution_mode_reasons"]
    assert corrected["_authoritative_turn_mode"] == "task_loop"
    assert corrected["turn_mode"] == "task_loop"
    assert "needs_visible_progress" in corrected["_authoritative_turn_mode_reasons"]


def test_apply_corrections_does_not_let_default_single_turn_hide_task_loop_candidate():
    layer = ControlLayer()

    corrected = layer.apply_corrections(
        {
            "turn_mode": "single_turn",
            "task_loop_candidate": True,
            "needs_visible_progress": True,
            "sequential_complexity": 8,
        },
        {
            "approved": True,
            "decision_class": "allow",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
        },
    )

    assert corrected["_authoritative_execution_mode"] == "task_loop"
    assert corrected["execution_mode"] == "task_loop"
    assert corrected["_authoritative_turn_mode"] == "task_loop"
    assert corrected["turn_mode"] == "task_loop"


def test_apply_corrections_does_not_let_default_direct_hide_task_loop_candidate():
    layer = ControlLayer()

    corrected = layer.apply_corrections(
        {
            "execution_mode": "direct",
            "turn_mode": "single_turn",
            "task_loop_candidate": True,
            "needs_visible_progress": True,
            "sequential_complexity": 8,
        },
        {
            "approved": True,
            "decision_class": "allow",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
        },
    )

    assert corrected["_authoritative_execution_mode"] == "task_loop"
    assert corrected["execution_mode"] == "task_loop"
    assert corrected["_authoritative_turn_mode"] == "task_loop"
    assert corrected["turn_mode"] == "task_loop"


def test_apply_corrections_defaults_to_single_turn_without_loop_candidate():
    layer = ControlLayer()

    corrected = layer.apply_corrections(
        {
            "task_loop_candidate": False,
            "needs_visible_progress": False,
            "sequential_complexity": 3,
        },
        {
            "approved": True,
            "decision_class": "allow",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
        },
    )

    assert corrected["_authoritative_execution_mode"] == "direct"
    assert corrected["execution_mode"] == "direct"
    assert corrected["_authoritative_turn_mode"] == "single_turn"
    assert corrected["turn_mode"] == "single_turn"


def test_apply_corrections_maps_confirmation_pending_to_interactive_defer():
    layer = ControlLayer()

    corrected = layer.apply_corrections(
        {
            "task_loop_candidate": False,
            "needs_visible_progress": False,
            "sequential_complexity": 2,
        },
        {
            "approved": True,
            "decision_class": "allow",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
            "_needs_skill_confirmation": True,
        },
    )

    assert corrected["_authoritative_execution_mode"] == "interactive_defer"
    assert corrected["execution_mode"] == "interactive_defer"
    assert corrected["_authoritative_turn_mode"] == "interactive_defer"
    assert corrected["turn_mode"] == "interactive_defer"
