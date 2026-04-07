from pathlib import Path


def _read(path: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / path).read_text(encoding='utf-8')


def test_approval_get_not_found_includes_explicit_error_code():
    src = _read('adapters/admin-api/commander_api/operations.py')
    assert "HTTPException(404, f\"Approval '{approval_id}' not found\")" in src
    assert 'error_code="not_found"' in src
    assert 'details={"approval_id": approval_id}' in src


def test_approval_approve_reject_not_found_include_error_contract_details():
    src = _read('adapters/admin-api/commander_api/operations.py')
    assert 'details={"approved": False, "approval_id": approval_id}' in src
    assert 'details={"rejected": False, "approval_id": approval_id}' in src
    assert src.count('error_code="not_found"') >= 3


def test_approval_start_failure_uses_system_start_failed_not_user():
    """
    Regression guard: when start_container raises after user approval,
    resolved_by must be 'system_start_failed' — never the approving user's
    identity.  Using the user identity here was misleading (implied the user
    rejected the request when actually the container crashed).
    """
    src = _read('container_commander/approval.py')
    # The fix: exception path must use the sentinel value
    assert '"system_start_failed"' in src
    # The bug: exception path must NOT propagate approved_by as resolved_by
    # Find the except block and verify approved_by is not used there
    marker = "Start after approve failed"
    except_idx = src.index(marker)
    except_block = src[except_idx: except_idx + 600]
    assert 'resolved_by = "system_start_failed"' in except_block
    assert 'resolved_by=approved_by' not in except_block
