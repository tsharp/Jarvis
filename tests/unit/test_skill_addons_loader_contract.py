import asyncio
from pathlib import Path


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_skill_addon_loader_exists_with_runtime_overlay_and_frontmatter_contract():
    src = _read("intelligence_modules/skill_addons/loader.py")
    assert "RUNTIME_ADDONS_ROOT" in src
    assert "TRION_SKILL_ADDONS_RUNTIME_DIR" in src
    assert "MARKETPLACE_DIR" in src
    assert "def _parse_frontmatter(" in src
    assert "yaml.safe_load" in src
    assert "def _infer_query_tags(" in src
    assert "async def load_skill_addon_context(" in src
    assert "_embedding_refine_sections" in src
    assert '"runtime_snapshot"' in src or "runtime_snapshot" in src


def test_skill_addon_loader_selects_runtime_and_answering_docs_for_inventory_question():
    from intelligence_modules.skill_addons.loader import load_skill_addon_context

    out = asyncio.run(
        load_skill_addon_context(
            query="Welche Skills hast du gerade installiert?",
            runtime_snapshot={"installed_count": 2, "draft_count": 1},
            max_docs=3,
            use_embeddings=False,
        )
    )

    ids = {item.get("id") for item in out.get("selected_docs", [])}
    assert "skill-runtime-skills" in ids
    assert "skill-answering-rules" in ids
    assert "runtime_skills" in out.get("inferred_tags", [])
    assert "answering_rules" in out.get("inferred_tags", [])


def test_skill_addon_loader_selects_tools_boundary_for_tools_question():
    from intelligence_modules.skill_addons.loader import load_skill_addon_context

    out = asyncio.run(
        load_skill_addon_context(
            query="Was ist der Unterschied zwischen Tools und Skills?",
            max_docs=3,
            use_embeddings=False,
        )
    )

    ids = {item.get("id") for item in out.get("selected_docs", [])}
    assert "skill-tools-vs-skills" in ids
    assert "tools_vs_skills" in out.get("inferred_tags", [])


def test_skill_addon_loader_does_not_copy_runtime_counts_into_semantic_context():
    from intelligence_modules.skill_addons.loader import load_skill_addon_context

    out = asyncio.run(
        load_skill_addon_context(
            query="Welche Skills hast du?",
            runtime_snapshot={"installed_count": 777, "draft_count": 555},
            max_docs=2,
            use_embeddings=False,
        )
    )

    context_text = str(out.get("context_text") or "")
    assert "777" not in context_text
    assert "555" not in context_text
