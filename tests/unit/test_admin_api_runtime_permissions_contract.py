from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_admin_api_image_prepares_runtime_volumes_before_dropping_privileges():
    dockerfile = (ROOT / "adapters/admin-api/Dockerfile").read_text(encoding="utf-8")
    entrypoint = (
        ROOT / "adapters/admin-api/docker-entrypoint.sh"
    ).read_text(encoding="utf-8")

    assert "util-linux" in dockerfile
    assert "COPY adapters/admin-api/docker-entrypoint.sh /usr/local/bin/jarvis-admin-api-entrypoint" in dockerfile
    assert 'ENTRYPOINT ["jarvis-admin-api-entrypoint"]' in dockerfile
    assert "TRION_HOME_DIR=\"${TRION_HOME_DIR:-/trion-home}\"" in entrypoint
    assert "prepare_writable_dir \"$TRION_HOME_DIR\"" in entrypoint
    assert "prepare_writable_dir \"$APP_DATA_DIR\"" in entrypoint
    assert "prepare_writable_dir \"$PROTOCOL_DIR\"" in entrypoint
    assert "chown -R \"${APP_UID}:${APP_GID}\"" in entrypoint
    assert "DOCKER_SOCK_GID=" in entrypoint
    assert "--groups=\"${SET_PRIV_GROUPS}\"" in entrypoint
    assert "export HOME=\"$HOME_DIR\"" in entrypoint


def test_admin_api_compose_does_not_override_entrypoint_user():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    service_start = compose.index("  jarvis-admin-api:")
    service_end = compose.index("\n  mcp-sql-memory:", service_start)
    service_block = compose[service_start:service_end]

    assert "trion_home_data:/trion-home" in service_block
    assert "commander-data:/app/data" in service_block
    assert "storage-broker-data:/app/storage_broker" in service_block
    assert "\n    group_add:" in service_block
    assert "- '988'" in service_block
    assert "\n    user:" not in service_block


def test_ops_scripts_run_admin_exec_writes_as_app_user():
    scripts = [
        ROOT / "scripts/ops/trion_live_restore.sh",
        ROOT / "scripts/ops/trion_restore.sh",
        ROOT / "scripts/ops/trion_live_reset.sh",
        ROOT / "scripts/ops/trion_reset.sh",
    ]

    for script in scripts:
        body = script.read_text(encoding="utf-8")
        assert 'ADMIN_EXEC_USER="${TRION_ADMIN_EXEC_USER:-1000:1000}"' in body
        assert 'docker exec --user "${ADMIN_EXEC_USER}"' in body

    diagnose = (ROOT / "scripts/ops/trion_diagnose.sh").read_text(encoding="utf-8")
    assert 'docker exec --user "${TRION_ADMIN_EXEC_USER:-1000:1000}"' in diagnose


def test_release_clean_waits_for_admin_api_after_restart_before_diagnose():
    script = (ROOT / "scripts/ops/trion_release_clean.sh").read_text(encoding="utf-8")

    assert "wait_http_ready()" in script
    assert 'wait_http_ready "Admin API" "${ADMIN_API_BASE}/health"' in script
    assert (
        'wait_http_ready "Runtime digest endpoint" '
        '"${ADMIN_API_BASE}/api/runtime/digest-state"'
    ) in script
    assert 'do_cmd bash "${DIAG_SCRIPT}" --quick' in script
