from pathlib import Path


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding="utf-8")


def test_skill_addons_taxonomy_files_exist():
    root = Path(__file__).resolve().parents[2] / "intelligence_modules" / "skill_addons" / "taxonomy"
    assert (root / "00-overview.md").exists()
    assert (root / "10-runtime-skills.md").exists()
    assert (root / "20-drafts.md").exists()
    assert (root / "30-tools-vs-skills.md").exists()
    assert (root / "40-session-skills.md").exists()
    assert (root / "50-answering-rules.md").exists()


def test_skill_addon_spec_forbids_second_inventory_truth_source():
    spec = _read("intelligence_modules/skill_addons/ADDON_SPEC.md")
    assert "keine zweite Truth-Source fuer konkrete Skill-Inventare" in spec
    assert "Ein Skill Addon darf nicht:" in spec
    assert "konkrete Counts enthalten" in spec
    assert "aktuelle Namenslisten pflegen" in spec
    assert "Installationsstatus einzelner Skills behaupten" in spec


def test_skill_taxonomy_guardrails_capture_core_boundaries():
    overview = _read("intelligence_modules/skill_addons/taxonomy/00-overview.md")
    runtime = _read("intelligence_modules/skill_addons/taxonomy/10-runtime-skills.md")
    tools = _read("intelligence_modules/skill_addons/taxonomy/30-tools-vs-skills.md")
    session = _read("intelligence_modules/skill_addons/taxonomy/40-session-skills.md")
    rules = _read("intelligence_modules/skill_addons/taxonomy/50-answering-rules.md")

    assert "Built-in Tools" in overview
    assert "Session-/System-Skills" in overview
    assert "`list_skills` deckt nur installierte Runtime-Skills ab." in runtime
    assert "`list_skills` deckt nicht die komplette Faehigkeitenwelt ab." in tools
    assert "nicht automatisch Teil der TRION Runtime-Skill-Registry" in session
    assert "Built-in Tools nicht als installierte Skills darstellen." in rules
