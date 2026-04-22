from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_task_loop_readme_documents_control_vs_routing_authority_boundary():
    src = _read("core/task_loop/README.md")

    required_markers = [
        "Autoritaetsgrenze: Control vs Routing",
        "active_task_loop_present",
        "Control bestimmt nur den groben Runtime-Modus.",
        "Routing entscheidet final ueber das Handoff.",
        "Resume-vs-Background ist ein Routing-Detail, kein Control-Reason.",
        "task_loop_active_reason_detail",
        "task_loop_routing_branch",
        "meta_turn_background_preserved",
        "independent_tool_turn_background_preserved",
    ]
    for marker in required_markers:
        assert marker in src


def test_obsidian_note_documents_handoff_authority_contract():
    src = _read("docs/obsidian/2026-04-22-task-loop-handoff-authority.md")

    required_markers = [
        "# Task-Loop Handoff Authority",
        "active_task_loop_present",
        "Routing ist die einzige Resume-vs-Background-Autoritaet",
        "runtime_resume_candidate",
        "meta_turn_background_preserved",
        "independent_tool_turn_background_preserved",
        "task_loop_active_reason",
        "task_loop_active_reason_detail",
        "task_loop_routing_branch",
    ]
    for marker in required_markers:
        assert marker in src
