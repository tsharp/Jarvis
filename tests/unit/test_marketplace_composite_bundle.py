import io
import json
import tarfile
from pathlib import Path

import yaml

from container_commander import marketplace
from container_commander.models import Blueprint


def _build_bundle_bytes(*, blueprint_id: str = "gaming-station", with_package: bool = True) -> bytes:
    payload = {
        "id": blueprint_id,
        "name": "Gaming Station",
        "description": "Composite bundle test",
        "dockerfile": "FROM alpine:3.20\nCMD [\"sh\"]",
        "network": "internal",
        "resources": {"cpu_limit": "1.0", "memory_limit": "512m"},
        "tags": ["gaming"],
    }
    bp_yaml = yaml.safe_dump(payload, sort_keys=False)
    meta = {
        "id": blueprint_id,
        "name": "Gaming Station",
        "version": "1.0.0",
        "checksum": marketplace.hashlib.sha256(bp_yaml.encode()).hexdigest(),
    }
    package = {
        "id": blueprint_id,
        "package_type": "composite_addon",
        "host_companion": {"id": "sunshine-host-bridge"},
        "container_addons": {
            "install_root": "runtime_addons",
            "profiles": ["profiles/gaming-station/00-profile.md"],
        },
    }

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in {
            "blueprint.yaml": bp_yaml,
            "meta.json": json.dumps(meta),
            "README.md": "# test\n",
            **({"package.json": json.dumps(package)} if with_package else {}),
        }.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if with_package:
            data = b"allowed_users=anybody\nneeds_root_rights=yes\n"
            info = tarfile.TarInfo("package/host/etc/X11/Xwrapper.config")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
            addon_data = b"---\ntitle: Gaming Station Profile\n---\n# Profile\n"
            info = tarfile.TarInfo("container_addons/profiles/gaming-station/00-profile.md")
            info.size = len(addon_data)
            tar.addfile(info, io.BytesIO(addon_data))
    return buf.getvalue()


def test_import_bundle_installs_composite_package_files(tmp_path, monkeypatch):
    monkeypatch.setattr(marketplace, "MARKETPLACE_DIR", str(tmp_path / "marketplace"))
    monkeypatch.setattr(marketplace, "REPO_ROOT", tmp_path)

    from container_commander import blueprint_store

    monkeypatch.setattr(blueprint_store, "get_blueprint", lambda _id: None)
    monkeypatch.setattr(blueprint_store, "create_blueprint", lambda bp: bp)
    monkeypatch.setattr(blueprint_store, "update_blueprint", lambda _id, data: Blueprint(**data))

    result = marketplace.import_bundle(_build_bundle_bytes(), filename="gaming-station.trion-bundle.tar.gz")

    assert result["imported"] is True
    assert result["package"]["installed"] is True
    package_root = tmp_path / "marketplace" / "packages" / "gaming-station"
    assert (package_root / "package.json").exists()
    assert (package_root / "host" / "etc" / "X11" / "Xwrapper.config").read_text(encoding="utf-8").startswith("allowed_users")
    addon_root = tmp_path / "runtime_addons"
    assert (addon_root / "profiles" / "gaming-station" / "00-profile.md").exists()
    assert result["container_addons"]["installed"] is True


def test_import_bundle_redirects_default_container_addon_root_to_marketplace_data(tmp_path, monkeypatch):
    monkeypatch.setattr(marketplace, "MARKETPLACE_DIR", str(tmp_path / "marketplace"))
    monkeypatch.setattr(marketplace, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(marketplace, "RUNTIME_CONTAINER_ADDONS_DIR", tmp_path / "marketplace" / "container_addons")

    from container_commander import blueprint_store

    monkeypatch.setattr(blueprint_store, "get_blueprint", lambda _id: None)
    monkeypatch.setattr(blueprint_store, "create_blueprint", lambda bp: bp)
    monkeypatch.setattr(blueprint_store, "update_blueprint", lambda _id, data: Blueprint(**data))

    payload = {
        "id": "gaming-station",
        "name": "Gaming Station",
        "description": "Composite bundle test",
        "dockerfile": "FROM alpine:3.20\nCMD [\"sh\"]",
        "network": "internal",
        "resources": {"cpu_limit": "1.0", "memory_limit": "512m"},
        "tags": ["gaming"],
    }
    bp_yaml = yaml.safe_dump(payload, sort_keys=False)
    meta = {
        "id": "gaming-station",
        "name": "Gaming Station",
        "version": "1.0.0",
        "checksum": marketplace.hashlib.sha256(bp_yaml.encode()).hexdigest(),
    }
    package = {
        "id": "gaming-station",
        "package_type": "composite_addon",
        "host_companion": {"id": "sunshine-host-bridge"},
        "container_addons": {
            "profiles": ["profiles/gaming-station/00-profile.md"],
        },
    }

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in {
            "blueprint.yaml": bp_yaml,
            "meta.json": json.dumps(meta),
            "README.md": "# test\n",
            "package.json": json.dumps(package),
        }.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        addon_data = b"---\ntitle: Gaming Station Profile\n---\n# Profile\n"
        info = tarfile.TarInfo("container_addons/profiles/gaming-station/00-profile.md")
        info.size = len(addon_data)
        tar.addfile(info, io.BytesIO(addon_data))

    result = marketplace.import_bundle(buf.getvalue(), filename="gaming-station.trion-bundle.tar.gz")

    addon_root = tmp_path / "marketplace" / "container_addons"
    assert result["container_addons"]["installed"] is True
    assert result["container_addons"]["root"] == str(addon_root)
    assert (addon_root / "profiles" / "gaming-station" / "00-profile.md").exists()


def test_install_catalog_blueprint_prefers_bundle_url(monkeypatch):
    monkeypatch.setattr(
        marketplace,
        "_load_catalog_cache",
        lambda: {
            "blueprints": [
                {
                    "id": "gaming-station",
                    "name": "Gaming Station",
                    "bundle_url": "https://example.invalid/gaming-station.trion-bundle.tar.gz",
                    "yaml_url": "https://example.invalid/gaming-station.yaml",
                }
            ]
        },
    )

    calls = {}

    def _fake_get_bytes(url: str, timeout: int = 30):
        calls["url"] = url
        calls["timeout"] = timeout
        return b"bundle-bytes"

    def _fake_import_bundle(raw, filename: str = "", overwrite: bool = False):
        calls["raw"] = raw
        calls["filename"] = filename
        calls["overwrite"] = overwrite
        return {"imported": True, "blueprint": {"id": "gaming-station"}}

    monkeypatch.setattr(marketplace, "_http_get_bytes", _fake_get_bytes)
    monkeypatch.setattr(marketplace, "import_bundle", _fake_import_bundle)

    result = marketplace.install_catalog_blueprint("gaming-station", overwrite=True)

    assert result["imported"] is True
    assert calls["url"].endswith("gaming-station.trion-bundle.tar.gz")
    assert calls["filename"] == "gaming-station.trion-bundle.tar.gz"
    assert calls["overwrite"] is True
    assert result["source"]["bundle_url"].endswith("gaming-station.trion-bundle.tar.gz")


def test_export_bundle_embeds_local_package_dir(tmp_path, monkeypatch):
    package_root = tmp_path / "packages"
    (package_root / "gaming-station").mkdir(parents=True)
    (package_root / "gaming-station" / "package.json").write_text(
        json.dumps(
            {
                "id": "gaming-station",
                "package_type": "composite_addon",
                "container_addons": {
                    "profiles": ["profiles/gaming-station/00-profile.md"],
                },
            }
        ),
        encoding="utf-8",
    )
    (package_root / "gaming-station" / "README.md").write_text("pkg readme", encoding="utf-8")
    addon_root = tmp_path / "container_addons"
    (addon_root / "profiles" / "gaming-station").mkdir(parents=True)
    (addon_root / "profiles" / "gaming-station" / "00-profile.md").write_text("# profile\n", encoding="utf-8")
    monkeypatch.setattr(marketplace, "LOCAL_PACKAGE_DIR", package_root)
    monkeypatch.setattr(marketplace, "LOCAL_CONTAINER_ADDONS_DIR", addon_root)
    monkeypatch.setattr(marketplace, "MARKETPLACE_DIR", str(tmp_path / "out"))

    from container_commander import blueprint_store

    bp = Blueprint(
        id="gaming-station",
        name="Gaming Station",
        description="Composite export test",
        dockerfile="FROM alpine:3.20\nCMD [\"sh\"]",
        tags=["gaming"],
    )
    monkeypatch.setattr(blueprint_store, "resolve_blueprint", lambda _id: bp)

    filename = marketplace.export_bundle("gaming-station")
    assert filename == "gaming-station.trion-bundle.tar.gz"

    bundle_path = tmp_path / "out" / filename
    with tarfile.open(bundle_path, "r:gz") as tar:
        names = set(tar.getnames())

    assert "blueprint.yaml" in names
    assert "package.json" in names
    assert "package/README.md" in names
    assert "container_addons/profiles/gaming-station/00-profile.md" in names


def test_export_import_roundtrip_uses_yaml_safe_blueprint_payload(tmp_path, monkeypatch):
    package_root = tmp_path / "packages"
    (package_root / "gaming-station-shadow").mkdir(parents=True)
    (package_root / "gaming-station-shadow" / "package.json").write_text(
        json.dumps({"id": "gaming-station-shadow", "package_type": "composite_addon"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(marketplace, "LOCAL_PACKAGE_DIR", package_root)
    monkeypatch.setattr(marketplace, "MARKETPLACE_DIR", str(tmp_path / "out"))

    state = {}

    def _resolve_blueprint(_id):
        return state.get(_id)

    def _get_blueprint(_id):
        return state.get(_id)

    def _create_blueprint(bp):
        state[bp.id] = bp
        return bp

    def _update_blueprint(_id, data):
        bp = Blueprint(**data)
        state[_id] = bp
        return bp

    from container_commander import blueprint_store

    bp = Blueprint(
        id="gaming-station-shadow",
        name="Gaming Station Shadow",
        description="Roundtrip export/import test",
        dockerfile="FROM alpine:3.20\nCMD [\"sh\"]",
        tags=["gaming", "shadow-test"],
    )
    state[bp.id] = bp
    monkeypatch.setattr(blueprint_store, "resolve_blueprint", _resolve_blueprint)
    monkeypatch.setattr(blueprint_store, "get_blueprint", _get_blueprint)
    monkeypatch.setattr(blueprint_store, "create_blueprint", _create_blueprint)
    monkeypatch.setattr(blueprint_store, "update_blueprint", _update_blueprint)

    filename = marketplace.export_bundle("gaming-station-shadow")
    assert filename == "gaming-station-shadow.trion-bundle.tar.gz"

    result = marketplace.import_bundle(str(tmp_path / "out" / filename), overwrite=True)

    assert result["imported"] is True
    assert result["blueprint"]["id"] == "gaming-station-shadow"
    assert result["package"]["package_id"] == "gaming-station-shadow"
