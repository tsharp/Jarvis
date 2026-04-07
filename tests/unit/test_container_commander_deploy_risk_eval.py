from container_commander.approval import evaluate_deploy_risk
from container_commander.models import Blueprint, NetworkMode


def test_evaluate_deploy_risk_flags_network_full():
    bp = Blueprint(
        id="web-bp",
        name="Web Blueprint",
        image="python:3.12-slim",
        network=NetworkMode.FULL,
    )

    risk = evaluate_deploy_risk(bp)

    assert risk["requires_approval"] is True
    assert "network_full" in risk["risk_flags"]
    assert any("network: full" in reason for reason in risk["reasons"])


def test_evaluate_deploy_risk_flags_dangerous_capability_and_seccomp_relaxation():
    bp = Blueprint(
        id="gaming-bp",
        name="Gaming Blueprint",
        image="josh5/steam-headless:latest",
        cap_add=["SYS_ADMIN", "CHOWN"],
        security_opt=["seccomp=unconfined"],
    )

    risk = evaluate_deploy_risk(bp)

    assert risk["requires_approval"] is True
    assert "cap_add:SYS_ADMIN" in risk["risk_flags"]
    assert "security_opt:seccomp=unconfined" in risk["risk_flags"]
    assert any("dangerous capability: SYS_ADMIN" in reason for reason in risk["reasons"])
    assert any("runtime security: seccomp=unconfined" in reason for reason in risk["reasons"])


def test_evaluate_deploy_risk_flags_privileged_mode():
    bp = Blueprint(
        id="vm-bp",
        name="VM Blueprint",
        image="alpine:3.20",
        privileged=True,
    )

    risk = evaluate_deploy_risk(bp)

    assert risk["requires_approval"] is True
    assert "privileged" in risk["risk_flags"]
    assert any("privileged mode" in reason for reason in risk["reasons"])


def test_evaluate_deploy_risk_is_clean_for_hardened_internal_blueprint():
    bp = Blueprint(
        id="safe-bp",
        name="Safe Blueprint",
        image="python:3.12-slim",
        network=NetworkMode.INTERNAL,
        cap_drop=["NET_RAW"],
        read_only_rootfs=True,
    )

    risk = evaluate_deploy_risk(bp)

    assert risk["requires_approval"] is False
    assert risk["reasons"] == []
    assert risk["risk_flags"] == []
    assert risk["cap_drop"] == ["NET_RAW"]
    assert risk["read_only_rootfs"] is True
