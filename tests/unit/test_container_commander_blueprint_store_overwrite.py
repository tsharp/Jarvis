from pathlib import Path

from container_commander import blueprint_store
from container_commander.models import Blueprint


def test_update_blueprint_can_clear_image_when_overwriting(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    monkeypatch.setattr(blueprint_store, "DB_PATH", str(db_path))
    monkeypatch.setattr(blueprint_store, "_INIT_DONE", False)

    created = blueprint_store.create_blueprint(
        Blueprint(
            id="gaming-station",
            name="Gaming Station",
            image="josh5/steam-headless:latest",
        )
    )
    assert created.image == "josh5/steam-headless:latest"

    updated = blueprint_store.update_blueprint(
        "gaming-station",
        {
            "dockerfile": "FROM josh5/steam-headless:latest\nRUN echo ok\n",
            "image": None,
        },
    )

    assert updated is not None
    assert updated.image is None
    assert updated.dockerfile.startswith("FROM josh5/steam-headless:latest")
