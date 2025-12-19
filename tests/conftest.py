import os
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app, db
from app.models import User


@pytest.fixture
def app_factory(tmp_path):
    created_apps = []

    def _create(**overrides):
        idx = len(created_apps)
        instance_dir = tmp_path / f"instance_{idx}"
        games_root = tmp_path / "games_root"
        legacy_dir = tmp_path / "legacy_templates_games"

        instance_dir.mkdir(parents=True, exist_ok=True)
        games_root.mkdir(parents=True, exist_ok=True)
        legacy_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test_{idx}.db",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "GAMES_ROOT": str(games_root),
            "LEGACY_GAMES_DIR": str(legacy_dir),
            "INSTANCE_PATH": str(instance_dir),
        }
        config.update(overrides)

        app = create_app(config)
        with app.app_context():
            db.create_all()
        created_apps.append(app)
        return app

    yield _create

    for app in created_apps:
        with app.app_context():
            db.session.remove()
            db.drop_all()


@pytest.fixture
def user_factory():
    def _create(app, username="user", password="password", is_admin=False):
        with app.app_context():
            user = User(username=username, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        return user

    return _create


@pytest.fixture
def login_helper():
    def _login(client, username, password):
        return client.post(
            "/auth/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    return _login
