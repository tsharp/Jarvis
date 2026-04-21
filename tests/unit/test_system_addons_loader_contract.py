from pathlib import Path

import pytest

from intelligence_modules.system_addons.loader import load_system_addon_context


_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (_ROOT / path).read_text(encoding="utf-8")


# ── Statische Struktur ──────────────────────────────────────────────────────

def test_system_addon_docs_exist():
    base = _ROOT / "intelligence_modules" / "system_addons"
    assert (base / "topology" / "00-services.md").exists()
    assert (base / "topology" / "10-data-locations.md").exists()
    assert (base / "topology" / "20-auth-model.md").exists()
    assert (base / "topology" / "30-tool-surface.md").exists()
    assert (base / "self_extension" / "00-skill-lifecycle.md").exists()
    assert (base / "self_extension" / "10-safe-paths.md").exists()
    assert (base / "self_extension" / "20-alias-model.md").exists()


def test_system_addon_loader_source_contract():
    src = _read("intelligence_modules/system_addons/loader.py")
    assert "def _parse_frontmatter(" in src
    assert "yaml.safe_load" in src
    assert "async def load_system_addon_context(" in src
    assert "embed_text" in src
    assert "_embedding_refine_sections" in src
    assert '"topology", "self_extension"' in src
    assert "query_class" in src
    assert "_QUERY_CLASS_CONFIG" in src


def test_all_addon_docs_have_valid_frontmatter():
    import yaml
    base = _ROOT / "intelligence_modules" / "system_addons"
    for path in base.rglob("*.md"):
        if path.name.lower() in ("readme.md", "addon_spec.md"):
            continue
        raw = path.read_text(encoding="utf-8")
        assert raw.startswith("---\n"), f"{path.name}: fehlt Frontmatter-Start"
        end = raw.find("\n---\n", 4)
        assert end > 0, f"{path.name}: fehlt Frontmatter-Ende"
        fm_text = raw[4:end]
        meta = yaml.safe_load(fm_text)
        assert isinstance(meta, dict), f"{path.name}: Frontmatter kein dict"
        assert "id" in meta, f"{path.name}: fehlt 'id'"
        assert "scope" in meta, f"{path.name}: fehlt 'scope'"
        assert "priority" in meta, f"{path.name}: fehlt 'priority'"


# ── Loader-Verhalten ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_loader_returns_topology_docs_for_system_topology_query_class():
    result = await load_system_addon_context(
        intent="Auf welchem Port läuft jarvis-admin-api und welche Services gibt es?",
        query_class="system_topology",
        use_embeddings=False,
    )
    selected = list(result.get("selected_docs") or [])
    assert selected, "Keine Docs zurückgegeben"
    assert result.get("query_class") == "system_topology"
    assert all("/topology/" in str(item.get("path") or "") for item in selected)
    assert any("topology" in str(item.get("scope") or "").lower() for item in selected)


@pytest.mark.asyncio
async def test_loader_returns_data_locations_docs_for_data_locations_query_class():
    result = await load_system_addon_context(
        intent="Wo liegen API-Keys und Secrets? Wie greife ich auf sie zu?",
        query_class="data_locations",
        use_embeddings=False,
    )
    selected = list(result.get("selected_docs") or [])
    assert selected
    assert result.get("query_class") == "data_locations"
    assert all("/topology/" in str(item.get("path") or "") for item in selected)
    assert any("data_locations" in str(item.get("scope") or "") for item in selected)


@pytest.mark.asyncio
async def test_loader_returns_self_extension_docs_for_self_extension_query_class():
    result = await load_system_addon_context(
        intent="Ich will einen neuen Skill erstellen. Wie läuft das ab?",
        query_class="self_extension",
        use_embeddings=False,
    )
    selected = list(result.get("selected_docs") or [])
    assert selected
    assert result.get("query_class") == "self_extension"
    assert all("/self_extension/" in str(item.get("path") or "") for item in selected)


@pytest.mark.asyncio
async def test_loader_respects_max_docs():
    result = await load_system_addon_context(
        intent="services tools secrets",
        query_class="",
        max_docs=2,
        use_embeddings=False,
    )
    assert len(list(result.get("selected_docs") or [])) <= 2


@pytest.mark.asyncio
async def test_loader_respects_max_chars():
    result = await load_system_addon_context(
        intent="services",
        max_chars=100,
        use_embeddings=False,
    )
    assert len(result.get("context_text") or "") <= 100


@pytest.mark.asyncio
async def test_loader_unknown_query_class_returns_empty_string():
    result = await load_system_addon_context(
        intent="anything",
        query_class="does_not_exist",
        use_embeddings=False,
    )
    assert result.get("query_class") == ""


@pytest.mark.asyncio
async def test_loader_does_not_cross_dirs_for_topology_query_class():
    result = await load_system_addon_context(
        intent="skill erstellen lifecycle",
        query_class="system_topology",
        use_embeddings=False,
    )
    selected = list(result.get("selected_docs") or [])
    assert all("/self_extension/" not in str(item.get("path") or "") for item in selected)


@pytest.mark.asyncio
async def test_loader_context_text_is_non_empty_for_matching_intent():
    result = await load_system_addon_context(
        intent="wo liegen secrets api keys vault",
        query_class="data_locations",
        use_embeddings=False,
    )
    assert result.get("context_text", "").strip()
