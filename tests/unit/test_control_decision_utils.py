from core.control_decision_utils import (
    build_control_workspace_summary,
    build_done_workspace_summary,
    is_control_hard_block_decision,
    make_hard_block_verification,
    normalize_block_reason_code,
    normalize_control_verification,
    soften_control_deny,
)


def test_normalize_block_reason_code_sanitizes_symbols():
    assert normalize_block_reason_code("Critical CIM / Policy-Check") == "critical_cim_policy_check"


def test_make_hard_block_verification_sets_required_fields():
    out = make_hard_block_verification(
        reason_code="malicious_intent",
        warnings=["danger"],
    )
    assert out["approved"] is False
    assert out["hard_block"] is True
    assert out["decision_class"] == "hard_block"
    assert out["block_reason_code"] == "malicious_intent"


def test_is_control_hard_block_decision_false_for_soft_warning_shape():
    verification = {
        "approved": False,
        "hard_block": False,
        "decision_class": "warn",
        "block_reason_code": "",
        "warnings": ["Needs memory but no keys specified"],
    }
    assert is_control_hard_block_decision(verification) is False


def test_normalize_control_verification_keeps_deny_blocked():
    verification = {
        "approved": False,
        "reason": "",
        "warnings": [],
    }
    out = normalize_control_verification(verification)
    assert out["approved"] is False
    assert out["decision_class"] == "deny"
    assert out["hard_block"] is False
    assert out["reason"] == "control_denied"


def test_soften_control_deny_compat_no_longer_approves():
    verification = {
        "approved": False,
        "reason": "needs clarification",
        "warnings": ["ambiguous"],
    }
    out = soften_control_deny(verification)
    assert out["approved"] is False
    assert out["decision_class"] == "deny"
    assert out["hard_block"] is False


def test_workspace_summary_helpers_are_stable():
    ctrl = build_control_workspace_summary(
        {"approved": True, "warnings": ["x"], "corrections": {"needs_memory": True}},
        skipped=False,
        skip_reason="",
    )
    done = build_done_workspace_summary("stop", response_mode="interactive", model="m", memory_used=True)
    assert "approved=True" in ctrl
    assert "warnings=1" in ctrl
    assert "done_reason=stop" in done
    assert "response_mode=interactive" in done
