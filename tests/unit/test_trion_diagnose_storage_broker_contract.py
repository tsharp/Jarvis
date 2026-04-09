from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_trion_diagnose_includes_storage_broker_services():
    source = (ROOT / "scripts/ops/trion_diagnose.sh").read_text(encoding="utf-8")
    start = source.index("SERVICE_CONTAINERS=(")
    end = source.index(")", start)
    block = source[start:end]

    assert "storage-host-helper" in block
    assert "storage-broker" in block
