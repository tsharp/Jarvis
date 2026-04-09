from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_storage_broker_image_prepares_named_volume_before_dropping_privileges():
    dockerfile = (ROOT / "mcp-servers/storage-broker/Dockerfile").read_text(encoding="utf-8")
    entrypoint = (
        ROOT / "mcp-servers/storage-broker/docker-entrypoint.sh"
    ).read_text(encoding="utf-8")

    assert "COPY docker-entrypoint.sh /usr/local/bin/storage-broker-entrypoint" in dockerfile
    assert 'ENTRYPOINT ["storage-broker-entrypoint"]' in dockerfile
    assert "chown -R \"${APP_UID}:${APP_GID}\"" in entrypoint
    assert "export HOME=\"$HOME_DIR\"" in entrypoint
    assert "export XDG_DATA_HOME=" in entrypoint
    assert "export XDG_CACHE_HOME=" in entrypoint
    assert "setpriv" in entrypoint
    assert "--groups=\"${APP_GID},6\"" in entrypoint


def test_storage_broker_compose_does_not_override_entrypoint_user():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    service_start = compose.index("  storage-broker:")
    service_end = compose.index("\nvolumes:", service_start)
    service_block = compose[service_start:service_end]

    assert "storage-broker-data:/app/data" in service_block
    assert "\n    user:" not in service_block
