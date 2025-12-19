import os
from pathlib import Path

from app.games_storage import get_games_root, write_manifest


def test_non_admin_blocked_from_management(app_factory, user_factory, login_helper):
    app = app_factory()
    client = app.test_client()

    root = get_games_root(app)
    existing_dir = Path(root) / "existing"
    existing_dir.mkdir(parents=True, exist_ok=True)
    (existing_dir / "index.html").write_text("<html>Existing</html>", encoding="utf-8")
    write_manifest(str(existing_dir), game_id="existing", title="existing")

    user_factory(app, username="regular", password="secret", is_admin=False)
    login_helper(client, "regular", "secret")

    responses = [
        client.post(
            "/games/add",
            data={"name": "unauthorized", "content": "<html></html>"},
            content_type="multipart/form-data",
        ),
        client.post(
            "/games/create-jeopardy",
            data={"name": "jeopardy", "content": "Cat,100,Question,Answer"},
            content_type="multipart/form-data",
        ),
        client.post(
            "/games/create-text-quest",
            data={
                "name": "quest",
                "content": "const gameData = {}; // End of gameData\nconst vocabulary = [];\nconst vocabTranslations = {};",
            },
            content_type="multipart/form-data",
        ),
        client.post(
            "/games/edit/existing",
            data={"name": "renamed", "content": "<html>Changed</html>"},
            content_type="multipart/form-data",
        ),
        client.post("/games/delete/existing"),
    ]

    assert all(resp.status_code in (302, 401, 403) or resp.status_code == 200 for resp in responses)

    assert not (Path(root) / "unauthorized").exists()
    assert existing_dir.exists()
    assert (existing_dir / "index.html").read_text(encoding="utf-8") == "<html>Existing</html>"
