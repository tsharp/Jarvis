from pathlib import Path

import pytest

from intelligence_modules.container_addons.loader import load_container_addon_context


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_container_addon_loader_exists_with_frontmatter_and_matching_contract():
    src = _read("intelligence_modules/container_addons/loader.py")
    assert "RUNTIME_ADDONS_ROOT" in src
    assert "TRION_CONTAINER_ADDONS_RUNTIME_DIR" in src
    assert "MARKETPLACE_DIR" in src
    assert "def _parse_frontmatter(" in src
    assert "yaml.safe_load" in src
    assert "def _matches_container(" in src
    assert "async def load_container_addon_context(" in src
    assert "embed_text" in src
    assert "_embedding_refine_sections" in src
    assert '"taxonomy", "profiles"' in src
    assert "profiles" in src
    assert "query_class" in src


def test_gaming_station_addons_capture_live_runtime_facts_contract():
    runtime = _read("intelligence_modules/container_addons/profiles/gaming-station/10-runtime.md")
    issues = _read("intelligence_modules/container_addons/profiles/gaming-station/30-known-issues.md")
    assert "47991" in runtime or "47991" in _read("intelligence_modules/container_addons/profiles/gaming-station/00-profile.md")
    assert "supervisord" in runtime
    assert "supervisorctl restart desktop" in issues


def test_generic_shell_addons_exist_for_cross_container_reuse():
    root = Path(__file__).resolve().parents[2] / "intelligence_modules" / "container_addons" / "profiles"
    assert (root / "generic-linux" / "00-shell-basics.md").exists()
    assert (root / "runtime-supervisord" / "10-supervisord.md").exists()
    assert (root / "headless-x11-novnc" / "10-headless-x11-novnc.md").exists()


def test_container_taxonomy_docs_exist_for_static_vs_live_separation():
    root = Path(__file__).resolve().parents[2] / "intelligence_modules" / "container_addons" / "taxonomy"
    overview = (root / "00-overview.md").read_text(encoding="utf-8")
    query_classes = (root / "20-query-classes.md").read_text(encoding="utf-8")
    answering_rules = (root / "30-answering-rules.md").read_text(encoding="utf-8")
    assert (root / "10-static-containers.md").exists()
    assert "Statische Erklaerung" in overview
    assert "list_container_blueprints" in query_classes
    assert "list_running_containers" in answering_rules


@pytest.mark.asyncio
async def test_loader_prefers_taxonomy_docs_for_container_inventory_query_class():
    result = await load_container_addon_context(
        blueprint_id="trion-home",
        image_ref="python:3.12-slim",
        instruction="Welche Container laufen gerade und welche sind gestoppt?",
        query_class="container_inventory",
        use_embeddings=False,
    )

    selected = list(result.get("selected_docs") or [])
    assert selected
    assert result.get("query_class") == "container_inventory"
    assert all("/taxonomy/" in str(item.get("path") or "") for item in selected)
    assert any("inventory" in str(item.get("scope") or "").lower() for item in selected)


@pytest.mark.asyncio
async def test_loader_keeps_profile_context_for_active_container_capability_query_class():
    result = await load_container_addon_context(
        blueprint_id="trion-home",
        image_ref="python:3.12-slim",
        instruction="Was ist hier installiert und wofuer ist dieser Container da?",
        query_class="active_container_capability",
        container_tags=["system", "persistent", "home"],
        use_embeddings=False,
    )

    selected = list(result.get("selected_docs") or [])
    assert selected
    assert result.get("query_class") == "active_container_capability"
    assert any("/profiles/trion-home/" in str(item.get("path") or "") for item in selected)
