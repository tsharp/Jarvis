import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from container_commander.models import Blueprint, NetworkMode


def test_engine_uses_deploy_risk_evaluation_before_starting_container():
    docker_module = types.ModuleType("docker")
    docker_module.DockerClient = object
    docker_errors = types.ModuleType("docker.errors")
    docker_errors.DockerException = type("DockerException", (Exception,), {})
    docker_errors.NotFound = type("NotFound", (Exception,), {})
    docker_errors.APIError = type("APIError", (Exception,), {})
    docker_errors.BuildError = type("BuildError", (Exception,), {})
    docker_errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
    docker_module.errors = docker_errors
    secret_store_module = types.ModuleType("container_commander.secret_store")
    secret_store_module.get_secrets_for_blueprint = lambda *args, **kwargs: {}
    secret_store_module.get_secret_value = lambda *args, **kwargs: None
    secret_store_module.log_secret_access = lambda *args, **kwargs: None

    # Save the existing engine module (if any) so we can restore it after the
    # test — otherwise patch("container_commander.engine.*") in subsequent tests
    # would patch a *different* module object than the one those tests imported.
    _saved_engine = sys.modules.get("container_commander.engine")

    with patch.dict(sys.modules, {
        "docker": docker_module,
        "docker.errors": docker_errors,
        "container_commander.secret_store": secret_store_module,
    }):
        sys.modules.pop("container_commander.engine", None)
        engine = importlib.import_module("container_commander.engine")

    bp = Blueprint(
        id="gaming-station",
        name="Gaming Station",
        image="josh5/steam-headless:latest",
        network=NetworkMode.INTERNAL,
        cap_add=["SYS_ADMIN"],
    )
    request_approval_mock = Mock(return_value=SimpleNamespace(id="appr-1234"))

    with patch.object(engine, "resolve_blueprint", return_value=bp), \
         patch.object(engine, "_setup_host_companion_impl", return_value=None), \
         patch("container_commander.storage_scope.validate_blueprint_mounts", return_value=(True, "ok")), \
         patch("container_commander.mount_utils.ensure_bind_mount_host_dirs", return_value=None), \
         patch("container_commander.approval.evaluate_deploy_risk", return_value={
             "requires_approval": True,
             "reasons": [
                 "Container requests dangerous capability: SYS_ADMIN",
                 "Container relaxes runtime security: seccomp=unconfined",
             ],
             "risk_flags": ["cap_add:SYS_ADMIN", "security_opt:seccomp=unconfined"],
             "network_mode": "internal",
             "cap_add": ["SYS_ADMIN"],
             "security_opt": ["seccomp=unconfined"],
             "cap_drop": ["NET_RAW"],
             "read_only_rootfs": False,
         }), \
         patch("container_commander.approval.request_approval", request_approval_mock):
        with pytest.raises(engine.PendingApprovalError) as exc:
            engine.start_container("gaming-station")

    assert exc.value.approval_id == "appr-1234"
    assert "SYS_ADMIN" in exc.value.reason
    request_approval_mock.assert_called_once()
    kwargs = request_approval_mock.call_args.kwargs
    assert kwargs["risk_flags"] == ["cap_add:SYS_ADMIN", "security_opt:seccomp=unconfined"]
    assert kwargs["requested_cap_add"] == ["SYS_ADMIN"]
    assert kwargs["requested_security_opt"] == ["seccomp=unconfined"]
    assert kwargs["requested_cap_drop"] == ["NET_RAW"]
    assert kwargs["read_only_rootfs"] is False

    # Cleanup: restore the engine module that was in sys.modules before this test,
    # so subsequent tests that already hold a reference to it see a consistent state.
    if _saved_engine is not None:
        sys.modules["container_commander.engine"] = _saved_engine
    else:
        sys.modules.pop("container_commander.engine", None)
