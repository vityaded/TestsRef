import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from werkzeug.utils import secure_filename

LEGACY_MAP_FILENAME = "_legacy_map.json"


def get_games_root(app) -> str:
    root = app.config.get("GAMES_ROOT")
    if not root:
        root = os.path.join(app.instance_path, "games")
    os.makedirs(root, exist_ok=True)
    return root


def _legacy_map_path(root: str) -> str:
    return os.path.join(root, LEGACY_MAP_FILENAME)


def load_legacy_map(root: str) -> Dict[str, str]:
    path = _legacy_map_path(root)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_legacy_map(root: str, mapping: Dict[str, str]) -> None:
    os.makedirs(root, exist_ok=True)
    path = _legacy_map_path(root)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def is_reserved_legacy_template(filename: str) -> bool:
    name = filename.lower()
    return (
        name == "index.html"
        or name == "edit_game.html"
        or name.startswith("game_test")
    )


def sanitize_game_id(
    name: str,
    *,
    root: Optional[str] = None,
    existing_ids: Optional[Iterable[str]] = None,
    allow_existing: Optional[str] = None,
) -> str:
    base_id = secure_filename(name or "").lower()
    if not base_id:
        raise ValueError("Game id cannot be empty")

    existing: Set[str] = set(existing_ids or [])
    if root:
        try:
            for entry in os.listdir(root):
                if os.path.isdir(os.path.join(root, entry)):
                    existing.add(entry)
        except FileNotFoundError:
            pass

    candidate = base_id
    counter = 2
    while True:
        collision = False
        if candidate != allow_existing and candidate in existing:
            collision = True
        if (
            not collision
            and root
            and os.path.exists(os.path.join(root, candidate))
            and candidate != allow_existing
        ):
            collision = True
        if not collision:
            return candidate
        candidate = f"{base_id}-{counter}"
        counter += 1


def write_manifest(game_dir: str, *, game_id: str, title: str) -> None:
    manifest = {
        "id": game_id,
        "title": title,
        "entry": "index.html",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(game_dir, "manifest.json")
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def list_games(root: str) -> List[Dict[str, str]]:
    games = []
    if not os.path.isdir(root):
        return games

    for entry in os.listdir(root):
        game_dir = os.path.join(root, entry)
        if not os.path.isdir(game_dir):
            continue
        index_path = os.path.join(game_dir, "index.html")
        if not os.path.exists(index_path):
            continue

        name = entry
        manifest_path = os.path.join(game_dir, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    title = manifest.get("title")
                    if title:
                        name = title
            except (OSError, json.JSONDecodeError):
                pass
        games.append({"id": entry, "name": name})

    games.sort(key=lambda g: (g["name"], g["id"]))
    return games


def sanitize_asset_path(path_value: str) -> str:
    normalized = (path_value or "").replace("\\", "/")
    parts = normalized.split("/")
    sanitized_parts: List[str] = []

    for part in parts:
        if part in ("", ".", ".."):
            raise ValueError("Invalid path segment")
        cleaned = secure_filename(part)
        if not cleaned:
            raise ValueError("Invalid path segment")
        if cleaned.startswith("."):
            raise ValueError("Dotfiles are not allowed")
        if cleaned in {"manifest.json", LEGACY_MAP_FILENAME}:
            raise ValueError("File name is reserved")
        sanitized_parts.append(cleaned)

    rel_path = "/".join(sanitized_parts)
    if rel_path == "index.html":
        raise ValueError("index.html cannot be overwritten")
    if rel_path in {"manifest.json", LEGACY_MAP_FILENAME}:
        raise ValueError("Reserved file")
    return rel_path


def migrate_legacy_games(app) -> None:
    games_root = get_games_root(app)
    legacy_dir = app.config.get(
        "LEGACY_GAMES_DIR",
        os.path.join(app.root_path, "templates", "games"),
    )
    if not os.path.isdir(legacy_dir):
        return

    backup_dir = os.path.join(app.instance_path, "games_legacy_backup")
    os.makedirs(backup_dir, exist_ok=True)

    legacy_map = load_legacy_map(games_root)
    existing_targets = set(legacy_map.values())

    for filename in os.listdir(legacy_dir):
        if not filename.lower().endswith(".html"):
            continue
        if is_reserved_legacy_template(filename):
            continue

        legacy_path = os.path.join(legacy_dir, filename)
        if not os.path.isfile(legacy_path):
            continue

        legacy_id = Path(filename).stem
        target_id = legacy_map.get(legacy_id)
        if not target_id:
            target_id = sanitize_game_id(legacy_id, root=games_root, existing_ids=existing_targets)
            legacy_map[legacy_id] = target_id
            existing_targets.add(target_id)

        target_dir = os.path.join(games_root, target_id)
        os.makedirs(target_dir, exist_ok=True)
        target_index = os.path.join(target_dir, "index.html")

        if not os.path.exists(target_index):
            with open(legacy_path, "r", encoding="utf-8") as src:
                content = src.read()
            with open(target_index, "w", encoding="utf-8") as dst:
                dst.write(content)
            write_manifest(target_dir, game_id=target_id, title=legacy_id)

        backup_path = os.path.join(backup_dir, filename)
        if os.path.exists(legacy_path):
            shutil.move(legacy_path, backup_path)

    save_legacy_map(games_root, legacy_map)
