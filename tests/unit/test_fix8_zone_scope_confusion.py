"""
Tests für Fix #8: Zone vs. Scope Begriffsüberlappung

Storage Broker kennt Zonen (managed_services, backup, …).
Container Commander kennt Scopes (my-service_scope).
LLM verwechselt diese und setzt storage_scope="managed_services" in blueprint_create
→ storage_scope_missing Fehler zur Laufzeit.

Fixes:
A) blueprint_create erkennt Zonen-Namen früh und gibt klaren Fehler mit Tipp.
B) blueprint_create prüft ob der Scope wirklich registriert ist (early validation).
C) Tool-Beschreibungen machen die Unterscheidung explizit.
"""
from pathlib import Path
from unittest.mock import patch


def _mcp_src() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "container_commander/mcp_tools.py").read_text(encoding="utf-8")


# ── Fix A: Zone-name guard in blueprint_create ──────────

def test_blueprint_create_schema_storage_scope_warns_about_zones():
    """storage_scope description must explicitly warn against using zone names."""
    src = _mcp_src()
    bp_schema = src.split('"name": "blueprint_create"')[1].split('"name": "home_write"')[0]
    assert "Storage Broker zone" in bp_schema
    assert "managed_services" in bp_schema
    assert "storage_scope_upsert" in bp_schema


def test_blueprint_create_rejects_managed_services_as_scope():
    """blueprint_create must reject storage_scope='managed_services' with clear error."""
    import container_commander.mcp_tools as tools

    def fake_is_trusted(img): return True
    def fake_get_bp(bid): return None

    with patch.dict("sys.modules", {
        "container_commander.blueprint_store": __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock(
            get_blueprint=fake_get_bp,
            create_blueprint=None,
        ),
        "container_commander.models": __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock(),
        "container_commander.trust": __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock(
            is_trusted_image=fake_is_trusted,
        ),
    }):
        result = tools._tool_blueprint_create({
            "id": "my-service",
            "image": "python:3.12-slim",
            "name": "My Service",
            "storage_scope": "managed_services",
        })

    assert "error" in result
    assert "Storage Broker zone" in result["error"]
    assert "managed_services" in result["error"]
    assert "storage_scope_upsert" in result["error"] or "storage_provision_container" in result["error"]
    assert "hint" in result


def test_blueprint_create_rejects_all_known_zone_names():
    """All known Storage Broker zone names must be rejected when used as storage_scope."""
    import container_commander.mcp_tools as tools
    from unittest.mock import MagicMock

    zone_names = ["managed_services", "backup", "system", "external", "docker_runtime", "unzoned"]

    for zone in zone_names:
        with patch.dict("sys.modules", {
            "container_commander.blueprint_store": MagicMock(get_blueprint=lambda b: None),
            "container_commander.models": MagicMock(),
            "container_commander.trust": MagicMock(is_trusted_image=lambda i: True),
        }):
            result = tools._tool_blueprint_create({
                "id": "test-bp",
                "image": "python:3.12-slim",
                "name": "Test",
                "storage_scope": zone,
            })

        assert "error" in result, f"Zone '{zone}' should be rejected as storage_scope"
        assert "Storage Broker zone" in result["error"], f"Error for '{zone}' must explain it's a zone"


def test_blueprint_create_zone_guard_implementation_present():
    """_tool_blueprint_create must contain the zone-name guard."""
    src = _mcp_src()
    impl = src.split("def _tool_blueprint_create")[1].split("def _tool_home_write")[0]
    assert "_STORAGE_BROKER_ZONES" in impl
    assert "managed_services" in impl
    assert "Storage Broker zone" in impl


# ── Fix B: Early scope existence check ──────────────────

def test_blueprint_create_rejects_unknown_scope_name():
    """blueprint_create must reject storage_scope that isn't registered yet."""
    import container_commander.mcp_tools as tools
    from unittest.mock import MagicMock

    with patch.dict("sys.modules", {
        "container_commander.blueprint_store": MagicMock(get_blueprint=lambda b: None),
        "container_commander.models": MagicMock(),
        "container_commander.trust": MagicMock(is_trusted_image=lambda i: True),
        "container_commander.storage_scope": MagicMock(get_scope=lambda n: None),  # scope not found
    }):
        result = tools._tool_blueprint_create({
            "id": "my-service",
            "image": "python:3.12-slim",
            "name": "My Service",
            "storage_scope": "my-service_scope",
        })

    assert "error" in result
    assert "has not been registered" in result["error"] or "storage_scope_upsert" in result["error"]


def test_blueprint_create_accepts_registered_scope():
    """blueprint_create must proceed when storage_scope exists in the registry."""
    import container_commander.mcp_tools as tools
    from unittest.mock import MagicMock

    fake_scope = {"name": "my-service_scope", "roots": [{"path": "/data/svc", "mode": "rw"}]}
    created = {}

    class FakeBP:
        def __init__(self, **kw):
            self.__dict__.update(kw)
            self.id = kw.get("id", "bp")
            self.name = kw.get("name", "N")
            self.image = kw.get("image", "i")
            self.mounts = []

    def fake_create(bp):
        created["bp"] = bp
        return bp

    with patch.dict("sys.modules", {
        "container_commander.blueprint_store": MagicMock(
            get_blueprint=lambda b: None,
            create_blueprint=fake_create,
            sync_blueprint_to_graph=lambda bp, trust_level=None: None,
        ),
        "container_commander.models": MagicMock(
            Blueprint=FakeBP,
            MountDef=MagicMock(),
            ResourceLimits=MagicMock(),
            NetworkMode=str,
        ),
        "container_commander.trust": MagicMock(
            is_trusted_image=lambda i: True,
            evaluate_blueprint_trust=lambda bp: {"level": "verified"},
        ),
        "container_commander.storage_scope": MagicMock(get_scope=lambda n: fake_scope),
    }):
        result = tools._tool_blueprint_create({
            "id": "my-service",
            "image": "python:3.12-slim",
            "name": "My Service",
            "storage_scope": "my-service_scope",
        })

    assert "error" not in result
    assert result.get("created") is True


def test_blueprint_create_no_scope_skips_existence_check():
    """When storage_scope is empty/absent, no existence check is performed."""
    import container_commander.mcp_tools as tools
    from unittest.mock import MagicMock

    get_scope_calls = []

    class FakeBP:
        def __init__(self, **kw):
            self.__dict__.update(kw)
            self.id = kw.get("id", "bp")
            self.name = kw.get("name", "N")
            self.image = kw.get("image", "i")
            self.mounts = []

    with patch.dict("sys.modules", {
        "container_commander.blueprint_store": MagicMock(
            get_blueprint=lambda b: None,
            create_blueprint=lambda bp: bp,
            sync_blueprint_to_graph=lambda bp, trust_level=None: None,
        ),
        "container_commander.models": MagicMock(
            Blueprint=FakeBP,
            MountDef=MagicMock(),
            ResourceLimits=MagicMock(),
            NetworkMode=str,
        ),
        "container_commander.trust": MagicMock(
            is_trusted_image=lambda i: True,
            evaluate_blueprint_trust=lambda bp: {"level": "verified"},
        ),
        "container_commander.storage_scope": MagicMock(
            get_scope=lambda n: get_scope_calls.append(n) or None
        ),
    }):
        result = tools._tool_blueprint_create({
            "id": "simple-bp",
            "image": "python:3.12-slim",
            "name": "Simple",
            # no storage_scope
        })

    assert "error" not in result
    assert len(get_scope_calls) == 0, "get_scope must not be called when storage_scope is absent"


def test_blueprint_create_early_scope_check_implementation_present():
    """_tool_blueprint_create must check scope existence before saving."""
    src = _mcp_src()
    impl = src.split("def _tool_blueprint_create")[1].split("def _tool_home_write")[0]
    assert "get_scope" in impl
    assert "has not been registered" in impl or "storage_scope_upsert" in impl


# ── Fix C: Tool description hardening ───────────────────

def test_storage_scope_upsert_description_distinguishes_zones():
    """storage_scope_upsert description must clarify it's NOT a zone."""
    src = _mcp_src()
    upsert_block = src.split('"name": "storage_scope_upsert"')[1].split('"name": "storage_scope_delete"')[0]
    assert "NOT a Storage Broker zone" in upsert_block or "not a Storage Broker zone" in upsert_block.lower()
    assert "managed_services" in upsert_block


def test_storage_scope_upsert_name_field_warns_against_zone_names():
    """storage_scope_upsert name field description must warn against zone names."""
    src = _mcp_src()
    upsert_block = src.split('"name": "storage_scope_upsert"')[1].split('"name": "storage_scope_delete"')[0]
    # The name field description should explicitly say don't use zone names
    assert "managed_services" in upsert_block
    assert "backup" in upsert_block


def test_storage_provision_container_description_mentions_zone_scope_bridge():
    """storage_provision_container description must mention it prevents zone/scope confusion."""
    src = _mcp_src()
    provision_block = src.split('"name": "storage_provision_container"')[1].split('"inputSchema"')[0]
    assert "zone" in provision_block.lower()
    assert "scope" in provision_block.lower()
    assert "managed_services" in provision_block


# ── Integration: guard position is before blueprint save ──

def test_zone_guard_fires_before_scope_existence_check():
    """Zone guard must fire before the generic scope-existence check (no redundant get_scope call)."""
    import container_commander.mcp_tools as tools
    from unittest.mock import MagicMock

    get_scope_calls = []

    with patch.dict("sys.modules", {
        "container_commander.blueprint_store": MagicMock(get_blueprint=lambda b: None),
        "container_commander.models": MagicMock(),
        "container_commander.trust": MagicMock(is_trusted_image=lambda i: True),
        "container_commander.storage_scope": MagicMock(
            get_scope=lambda n: get_scope_calls.append(n) or None
        ),
    }):
        result = tools._tool_blueprint_create({
            "id": "test-bp",
            "image": "python:3.12-slim",
            "name": "Test",
            "storage_scope": "managed_services",  # zone name
        })

    assert "error" in result
    assert "Storage Broker zone" in result["error"]
    # Zone guard fires before get_scope is called
    assert len(get_scope_calls) == 0, "get_scope must NOT be called when zone guard fires"
