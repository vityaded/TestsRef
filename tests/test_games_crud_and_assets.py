import io
from pathlib import Path

from app.games_storage import get_games_root, load_legacy_map


def _login_admin(app, client, user_factory, login_helper):
    user_factory(app, username="admin", password="secret", is_admin=True)
    login_helper(client, "admin", "secret")


def _create_basic_game(client, name="Sample", content="<html>Game</html>"):
    return client.post(
        "/games/add",
        data={"name": name, "content": content},
        content_type="multipart/form-data",
    )


def test_admin_can_create_game_and_upload_assets(app_factory, user_factory, login_helper):
    app = app_factory()
    client = app.test_client()
    _login_admin(app, client, user_factory, login_helper)

    response = client.post(
        "/games/add",
        data={
            "name": "My Game",
            "content": "<html>Main</html>",
            "asset_files": (io.BytesIO(b"body { color: red; }"), "assets/style.css"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code in (302, 303)

    root = Path(get_games_root(app))
    game_dirs = list(root.iterdir())
    assert game_dirs
    game_dir = game_dirs[0]

    assert (game_dir / "index.html").exists()
    asset_path = game_dir / "assets" / "style.css"
    assert asset_path.exists()
    assert asset_path.read_text(encoding="utf-8") == "body { color: red; }"

    asset_response = client.get(f"/games/{game_dir.name}/assets/style.css")
    assert asset_response.status_code == 200
    assert b"body { color: red; }" in asset_response.data


def test_folder_upload_preserves_structure(app_factory, user_factory, login_helper):
    app = app_factory()
    client = app.test_client()
    _login_admin(app, client, user_factory, login_helper)

    client.post(
        "/games/add",
        data={
            "name": "Folder Game",
            "content": "<html>Main</html>",
            "asset_folder": [
                (io.BytesIO(b"console.log('hi');"), "folderA/js/app.js"),
                (io.BytesIO(b"logo"), "folderA/img/logo.png"),
            ],
        },
        content_type="multipart/form-data",
    )

    root = Path(get_games_root(app))
    game_dir = next(iter(root.iterdir()))

    assert (game_dir / "folderA" / "js" / "app.js").exists()
    assert (game_dir / "folderA" / "img" / "logo.png").exists()


def test_path_traversal_is_rejected(app_factory, user_factory, login_helper, tmp_path):
    app = app_factory()
    client = app.test_client()
    _login_admin(app, client, user_factory, login_helper)

    client.post(
        "/games/add",
        data={
            "name": "Safe",
            "content": "<html>Safe</html>",
            "asset_files": (io.BytesIO(b"evil"), "../evil.txt"),
            "asset_folder": [(io.BytesIO(b"still evil"), "a/../../evil.txt")],
        },
        content_type="multipart/form-data",
    )

    root = Path(get_games_root(app))
    game_dir = next(iter(root.iterdir()))

    assert not (tmp_path / "evil.txt").exists()
    assert not any(path.name == "evil.txt" for path in game_dir.rglob("*.txt"))


def test_rename_keeps_old_link_working(app_factory, user_factory, login_helper):
    app = app_factory()
    client = app.test_client()
    _login_admin(app, client, user_factory, login_helper)

    _create_basic_game(client, name="first", content="<html>First</html>")

    edit_response = client.post(
        "/games/edit/first",
        data={"name": "second", "content": "<html>Second</html>"},
        content_type="multipart/form-data",
    )
    assert edit_response.status_code in (302, 303)

    root = Path(get_games_root(app))
    assert (root / "second").exists()
    assert not (root / "first").exists()

    legacy_map = load_legacy_map(str(root))
    assert legacy_map.get("first") == "second"

    redirect_response = client.get("/games/first/", follow_redirects=False)
    assert redirect_response.status_code in (301, 302)
    assert redirect_response.headers["Location"].endswith("/games/second/")


def test_delete_removes_folder(app_factory, user_factory, login_helper):
    app = app_factory()
    client = app.test_client()
    _login_admin(app, client, user_factory, login_helper)

    _create_basic_game(client, name="todelete", content="<html>Delete</html>")
    root = Path(get_games_root(app))
    assert (root / "todelete").exists()

    delete_response = client.post("/games/delete/todelete")
    assert delete_response.status_code in (302, 303)

    assert not (root / "todelete").exists()
    not_found = client.get("/games/todelete/")
    assert not_found.status_code == 404
