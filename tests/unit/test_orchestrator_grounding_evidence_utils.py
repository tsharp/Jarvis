import json

from core.orchestrator_grounding_evidence_utils import build_grounding_evidence_entry


def test_grounding_evidence_entry_prefers_result_lines_for_key_facts():
    raw = json.dumps(
        {
            "success": True,
            "result": "CPU: X\nRAM: Y\nGPU: Z\nStorage: Q",
        }
    )
    entry = build_grounding_evidence_entry("run_skill", raw, "ok", "ref-1")
    facts = entry.get("key_facts", [])
    assert any("GPU: Z" in line for line in facts)
    assert entry.get("structured", {}).get("result")


def test_grounding_evidence_entry_formats_list_skills_summary():
    raw = json.dumps(
        {
            "installed": [{"name": "a"}, {"name": "b"}],
            "installed_count": 2,
            "available": [],
            "available_count": 0,
        }
    )
    entry = build_grounding_evidence_entry("list_skills", raw, "ok", "ref-2")
    assert "installed_count: 2" in entry.get("key_facts", [])
    assert "available_count: 0" in entry.get("key_facts", [])
    assert entry.get("structured", {}).get("installed_names") == ["a", "b"]


def test_grounding_evidence_entry_formats_list_draft_skills_summary():
    raw = json.dumps(
        {
            "drafts": [{"name": "draft_alpha"}, {"name": "draft_beta"}],
        }
    )
    entry = build_grounding_evidence_entry("list_draft_skills", raw, "ok", "ref-3")
    assert "draft_count: 2" in entry.get("key_facts", [])
    assert "draft_names: draft_alpha, draft_beta" in entry.get("key_facts", [])
    assert entry.get("structured", {}).get("draft_names") == ["draft_alpha", "draft_beta"]


def test_grounding_evidence_entry_preserves_container_list_structure():
    raw = json.dumps(
        {
            "containers": [
                {"blueprint_id": "trion-home", "status": "running"},
                {"blueprint_id": "filestash", "status": "stopped"},
            ],
            "count": 2,
            "filter": "all",
        }
    )
    entry = build_grounding_evidence_entry("container_list", raw, "ok", "ref-4")
    structured = entry.get("structured", {})
    assert structured.get("count") == 2
    assert structured.get("filter") == "all"
    assert structured.get("containers") == [
        {"blueprint_id": "trion-home", "status": "running"},
        {"blueprint_id": "filestash", "status": "stopped"},
    ]


def test_grounding_evidence_entry_preserves_blueprint_list_structure():
    raw = json.dumps(
        {
            "blueprints": [
                {"id": "python-sandbox", "name": "Python Sandbox"},
                {"id": "node-sandbox", "name": "Node Sandbox"},
            ],
            "count": 2,
        }
    )
    entry = build_grounding_evidence_entry("blueprint_list", raw, "ok", "ref-5")
    structured = entry.get("structured", {})
    assert structured.get("count") == 2
    assert structured.get("blueprints") == [
        {"id": "python-sandbox", "name": "Python Sandbox"},
        {"id": "node-sandbox", "name": "Node Sandbox"},
    ]


def test_grounding_evidence_entry_preserves_container_inspect_structure():
    raw = json.dumps(
        {
            "container_id": "ctr-home",
            "name": "trion-home",
            "blueprint_id": "trion-home",
            "status": "running",
            "running": True,
            "image": "python:3.12-slim",
            "network": "trion-sandbox",
        }
    )
    entry = build_grounding_evidence_entry("container_inspect", raw, "ok", "ref-6")
    structured = entry.get("structured", {})
    assert structured.get("container_id") == "ctr-home"
    assert structured.get("name") == "trion-home"
    assert structured.get("blueprint_id") == "trion-home"
    assert structured.get("status") == "running"
    assert structured.get("running") is True
