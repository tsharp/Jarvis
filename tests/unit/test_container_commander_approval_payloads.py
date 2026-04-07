from container_commander.approval import PendingApproval
from container_commander.models import NetworkMode


def test_pending_approval_to_dict_exposes_runtime_risk_fields():
    item = PendingApproval(
        blueprint_id="gaming-station",
        reason="approval required",
        network_mode=NetworkMode.BRIDGE,
        risk_flags=["network_bridge", "cap_add:SYS_ADMIN"],
        risk_reasons=[
            "Container requests host bridge access (network: bridge)",
            "Container requests dangerous capability: SYS_ADMIN",
        ],
        requested_cap_add=["SYS_ADMIN"],
        requested_security_opt=["seccomp=unconfined"],
        requested_cap_drop=["NET_RAW"],
        read_only_rootfs=True,
        mount_overrides=[{"host": "/data/games", "container": "/games", "asset_id": "games-lib"}],
        storage_scope_override="__auto__",
        device_overrides=["/dev/dri:/dev/dri"],
    )

    data = item.to_dict()

    assert data["risk_flags"] == ["network_bridge", "cap_add:SYS_ADMIN"]
    assert data["risk_reasons"][0].startswith("Container requests host bridge access")
    assert data["requested_cap_add"] == ["SYS_ADMIN"]
    assert data["requested_security_opt"] == ["seccomp=unconfined"]
    assert data["requested_cap_drop"] == ["NET_RAW"]
    assert data["read_only_rootfs"] is True
    assert data["mount_overrides"][0]["asset_id"] == "games-lib"
    assert data["storage_scope_override"] == "__auto__"
    assert data["device_overrides"] == ["/dev/dri:/dev/dri"]


def test_pending_approval_persist_roundtrip_keeps_runtime_risk_fields():
    item = PendingApproval(
        blueprint_id="gaming-station",
        reason="approval required",
        network_mode=NetworkMode.FULL,
        risk_flags=["network_full", "security_opt:seccomp=unconfined"],
        risk_reasons=[
            "Container requests internet access (network: full)",
            "Container relaxes runtime security: seccomp=unconfined",
        ],
        requested_cap_add=["SYS_ADMIN"],
        requested_security_opt=["seccomp=unconfined"],
        requested_cap_drop=["NET_RAW"],
        read_only_rootfs=False,
        mount_overrides=[{"host": "/data/games", "container": "/games", "asset_id": "games-lib"}],
        storage_scope_override="__auto__",
        device_overrides=["/dev/dri:/dev/dri"],
    )

    restored = PendingApproval.from_persist_dict(item.to_persist_dict())

    assert restored.risk_flags == ["network_full", "security_opt:seccomp=unconfined"]
    assert restored.risk_reasons[1] == "Container relaxes runtime security: seccomp=unconfined"
    assert restored.requested_cap_add == ["SYS_ADMIN"]
    assert restored.requested_security_opt == ["seccomp=unconfined"]
    assert restored.requested_cap_drop == ["NET_RAW"]
    assert restored.read_only_rootfs is False
    assert restored.mount_overrides[0]["asset_id"] == "games-lib"
    assert restored.storage_scope_override == "__auto__"
    assert restored.device_overrides == ["/dev/dri:/dev/dri"]
