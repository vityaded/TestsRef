from pathlib import Path

from app.games_storage import get_games_root, load_legacy_map


def test_migration_converts_legacy_html(app_factory, tmp_path):
    legacy_dir = tmp_path / "legacy_templates_games"
    legacy_dir.mkdir(parents=True, exist_ok=True)

    legacy_file = legacy_dir / "My Legacy Game.html"
    legacy_file.write_text("<html>Legacy Content</html>", encoding="utf-8")
    (legacy_dir / "index.html").write_text("skip me", encoding="utf-8")
    (legacy_dir / "game_test3.html").write_text("skip as reserved", encoding="utf-8")

    app = app_factory()
    root = get_games_root(app)
    legacy_map = load_legacy_map(root)

    assert "My Legacy Game" in legacy_map
    new_id = legacy_map["My Legacy Game"]

    migrated_index = Path(root) / new_id / "index.html"
    assert migrated_index.exists()
    assert migrated_index.read_text(encoding="utf-8") == "<html>Legacy Content</html>"

    backup_path = Path(app.instance_path) / "games_legacy_backup" / "My Legacy Game.html"
    assert backup_path.exists()


def test_index_lists_folder_games(app_factory, tmp_path):
    legacy_dir = tmp_path / "legacy_templates_games"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    (legacy_dir / "Listable.html").write_text("<html>Playable</html>", encoding="utf-8")

    app = app_factory()
    client = app.test_client()

    response = client.get("/games/")
    assert response.status_code == 200
    assert b"Listable" in response.data
