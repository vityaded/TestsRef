import csv
import io
import os
import re
import shutil
from typing import List

import segno
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user

from app.forms import (
    AddGameForm,
    CreateJeopardyForm,
    CreateTextQuestForm,
    EditGameForm,
)
from app.games_storage import (
    LEGACY_MAP_FILENAME,
    get_games_root,
    list_games,
    load_legacy_map,
    sanitize_asset_path,
    sanitize_game_id,
    save_legacy_map,
    write_manifest,
)
from app.utils import admin_required

games_bp = Blueprint("games", __name__, url_prefix="/games")


def _games_root() -> str:
    return get_games_root(current_app)


def _game_dir(game_id: str) -> str:
    return os.path.join(_games_root(), game_id)


def _resolve_game_directory(game_name: str):
    game_dir = _game_dir(game_name)
    if os.path.isdir(game_dir):
        return game_dir, None

    legacy_map = load_legacy_map(_games_root())
    mapped = legacy_map.get(game_name)
    if mapped:
        mapped_dir = _game_dir(mapped)
        if os.path.isdir(mapped_dir):
            return mapped_dir, mapped
    return None, None


def _save_uploaded_assets(game_dir: str) -> None:
    uploaded_files = []
    for key in ("asset_files", "asset_folder"):
        uploaded_files.extend(request.files.getlist(key))

    errors = []
    base_dir = os.path.realpath(game_dir)
    for storage in uploaded_files:
        if not storage or not storage.filename:
            continue
        try:
            rel_path = sanitize_asset_path(storage.filename)
        except ValueError as exc:
            errors.append(f"{storage.filename}: {exc}")
            continue

        destination = os.path.realpath(os.path.join(game_dir, rel_path))
        if not destination.startswith(base_dir + os.sep) and destination != base_dir:
            errors.append(f"{storage.filename}: invalid path")
            continue

        os.makedirs(os.path.dirname(destination), exist_ok=True)
        storage.save(destination)

    if errors:
        flash("Some assets were skipped: " + "; ".join(errors), "warning")


def _list_existing_files(game_dir: str) -> List[str]:
    files: List[str] = []
    for root, _, filenames in os.walk(game_dir):
        for filename in filenames:
            if filename in {"manifest.json", LEGACY_MAP_FILENAME} or filename.startswith("."):
                continue
            rel_path = os.path.relpath(os.path.join(root, filename), game_dir)
            files.append(rel_path.replace(os.sep, "/"))
    files.sort()
    return files


@games_bp.route("/")
def index():
    available_games = list_games(_games_root())
    add_game_form = AddGameForm()
    jeopardy_form = CreateJeopardyForm()
    text_quest_form = CreateTextQuestForm()

    return render_template(
        "games/index.html",
        games=available_games,
        add_game_form=add_game_form,
        jeopardy_form=jeopardy_form,
        text_quest_form=text_quest_form,
    )


def _parse_jeopardy_content(raw_text: str):
    reader = csv.reader(io.StringIO(raw_text))
    categories = []
    entries = {}

    for line_number, row in enumerate(reader, start=1):
        if not row or all(not cell.strip() for cell in row):
            continue

        if len(row) != 4:
            raise ValueError(
                f"Line {line_number}: expected 4 values (category, value, question, answer)."
            )

        category, value_text, question, answer = [cell.strip() for cell in row]

        if not category or not value_text or not question or not answer:
            raise ValueError(
                f"Line {line_number}: all fields (category, value, question, answer) are required."
            )

        try:
            value = int(value_text)
        except ValueError:
            raise ValueError(f"Line {line_number}: value should be a number.")

        if category not in entries:
            categories.append(category)
            entries[category] = []

        entries[category].append({"value": value, "question": question, "answer": answer})

    if not categories:
        raise ValueError("No valid questions were provided.")

    for category in categories:
        entries[category] = sorted(entries[category], key=lambda item: item["value"])

    return categories, entries


@games_bp.route("/add", methods=["POST"])
@admin_required
def add_game():
    form = AddGameForm()
    if form.validate_on_submit():
        try:
            game_id = sanitize_game_id(form.name.data, root=_games_root())
        except ValueError:
            flash("Invalid game name. Please use letters, numbers, or underscores.", "danger")
            return redirect(url_for("games.index"))

        game_dir = _game_dir(game_id)
        if os.path.exists(game_dir):
            flash("A game with this name already exists. Please choose another name.", "danger")
            return redirect(url_for("games.index"))

        os.makedirs(game_dir, exist_ok=True)
        index_path = os.path.join(game_dir, "index.html")
        with open(index_path, "w", encoding="utf-8") as game_file:
            game_file.write(form.content.data)

        write_manifest(game_dir, game_id=game_id, title=form.name.data.strip())
        _save_uploaded_assets(game_dir)

        flash("Game added successfully!", "success")
        return redirect(url_for("games.play", game_name=game_id))

    for field, errors in form.errors.items():
        for error in errors:
            flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")
    return redirect(url_for("games.index"))


@games_bp.route("/create-jeopardy", methods=["POST"])
@admin_required
def create_jeopardy():
    form = CreateJeopardyForm()

    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")
        return redirect(url_for("games.index"))

    try:
        game_id = sanitize_game_id(form.name.data, root=_games_root())
    except ValueError:
        flash("Invalid game name. Please use letters, numbers, or underscores.", "danger")
        return redirect(url_for("games.index"))

    game_dir = _game_dir(game_id)
    if os.path.exists(game_dir):
        flash("A game with this name already exists. Please choose another name.", "danger")
        return redirect(url_for("games.index"))

    try:
        categories, entries = _parse_jeopardy_content(form.content.data)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("games.index"))

    values = sorted({item["value"] for cat_items in entries.values() for item in cat_items})
    board = {
        category: {
            item["value"]: {"question": item["question"], "answer": item["answer"]}
            for item in entries[category]
        }
        for category in categories
    }

    meta_questions = []
    for category in categories:
        for item in entries[category]:
            meta_questions.append(item["question"])
    meta_description = ", ".join(meta_questions[:4])

    html_content = render_template(
        "game_templates/jeopardy.html",
        title=form.name.data.strip(),
        categories=categories,
        values=values,
        board=board,
        meta_description=meta_description,
    )

    os.makedirs(game_dir, exist_ok=True)
    index_path = os.path.join(game_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as game_file:
        game_file.write(html_content)

    write_manifest(game_dir, game_id=game_id, title=form.name.data.strip())
    _save_uploaded_assets(game_dir)

    flash("Jeopardy game created successfully!", "success")
    return redirect(url_for("games.play", game_name=game_id))


@games_bp.route("/create-text-quest", methods=["POST"])
@admin_required
def create_text_quest():
    form = CreateTextQuestForm()

    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")
        return redirect(url_for("games.index"))

    try:
        game_id = sanitize_game_id(form.name.data, root=_games_root())
    except ValueError:
        flash("Invalid game name. Please use letters, numbers, or underscores.", "danger")
        return redirect(url_for("games.index"))

    game_dir = _game_dir(game_id)
    if os.path.exists(game_dir):
        flash("A game with this name already exists. Please choose another name.", "danger")
        return redirect(url_for("games.index"))

    template_path = os.path.join(current_app.root_path, "templates", "games", "game_test3.html")

    try:
        with open(template_path, "r", encoding="utf-8") as template_file:
            base_template = template_file.read()
    except OSError:
        flash("Could not load the base text quest template. Please contact support.", "danger")
        return redirect(url_for("games.index"))

    user_content = form.content.data

    block_patterns = {
        "gameData": re.compile(
            r"const\s+gameData\s*=\s*\{.*?\};\s*//\s*End of gameData", re.DOTALL
        ),
        "vocabulary": re.compile(r"const\s+vocabulary\s*=\s*\[.*?\];", re.DOTALL),
        "vocabTranslations": re.compile(r"const\s+vocabTranslations\s*=\s*\{.*?\};", re.DOTALL),
    }

    extracted_blocks = {}
    try:
        for label, pattern in block_patterns.items():
            match = pattern.search(user_content)
            if not match:
                raise ValueError(f"Could not find '{label}' block in the provided content.")
            extracted_blocks[label] = match.group(0).strip()
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("games.index"))

    replacement_targets = {
        "gameData": block_patterns["gameData"],
        "vocabulary": block_patterns["vocabulary"],
        "vocabTranslations": block_patterns["vocabTranslations"],
    }

    updated_html = base_template
    try:
        for label, pattern in replacement_targets.items():
            updated_html, replacements = pattern.subn(
                lambda _: extracted_blocks[label], updated_html, count=1
            )
            if replacements == 0:
                raise ValueError(f"Could not replace '{label}' in the base template.")
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("games.index"))

    os.makedirs(game_dir, exist_ok=True)
    index_path = os.path.join(game_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as game_file:
        game_file.write(updated_html)

    write_manifest(game_dir, game_id=game_id, title=form.name.data.strip())
    _save_uploaded_assets(game_dir)

    flash("Text quest created successfully!", "success")
    return redirect(url_for("games.play", game_name=game_id))


@games_bp.route("/edit/<string:game_name>", methods=["GET", "POST"])
@admin_required
def edit_game(game_name):
    game_dir = _game_dir(game_name)

    if not os.path.isdir(game_dir):
        abort(404)

    form = EditGameForm()
    index_path = os.path.join(game_dir, "index.html")

    if request.method == "GET":
        try:
            with open(index_path, "r", encoding="utf-8") as game_file:
                form.name.data = game_name
                form.content.data = game_file.read()
        except OSError:
            flash("Could not load the game for editing. Please try again later.", "danger")
            return redirect(url_for("games.index"))

    if form.validate_on_submit():
        try:
            new_id = sanitize_game_id(
                form.name.data,
                root=_games_root(),
                allow_existing=game_name,
            )
        except ValueError:
            flash("Invalid game name. Please use letters, numbers, or underscores.", "danger")
            return render_template(
                "games/edit_game.html",
                form=form,
                original_game_name=game_name,
                existing_files=_list_existing_files(game_dir),
            )

        if new_id != game_name:
            new_dir = _game_dir(new_id)
            if os.path.exists(new_dir):
                flash("A game with this name already exists. Please choose another name.", "danger")
                return render_template(
                    "games/edit_game.html",
                    form=form,
                    original_game_name=game_name,
                    existing_files=_list_existing_files(game_dir),
                )
            shutil.move(game_dir, new_dir)
            legacy_map = load_legacy_map(_games_root())
            legacy_map[game_name] = new_id
            save_legacy_map(_games_root(), legacy_map)

            game_name = new_id
            game_dir = new_dir
            index_path = os.path.join(game_dir, "index.html")

        with open(index_path, "w", encoding="utf-8") as game_file:
            game_file.write(form.content.data)

        write_manifest(game_dir, game_id=game_name, title=form.name.data.strip())
        _save_uploaded_assets(game_dir)

        flash("Game updated successfully!", "success")
        return redirect(url_for("games.play", game_name=game_name))

    if request.method == "POST":
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")

    return render_template(
        "games/edit_game.html",
        form=form,
        original_game_name=game_name,
        existing_files=_list_existing_files(game_dir),
    )


@games_bp.route("/delete/<string:game_name>", methods=["POST"])
@admin_required
def delete_game(game_name):
    game_dir = _game_dir(game_name)

    if not os.path.isdir(game_dir):
        abort(404)

    try:
        shutil.rmtree(game_dir)
    except OSError:
        flash("Could not delete the game. Please try again later.", "danger")
    else:
        flash("Game deleted successfully.", "success")

    return redirect(url_for("games.index"))


@games_bp.route("/<string:game_name>/qr.png")
def game_qr_code(game_name: str):
    game_dir, mapped = _resolve_game_directory(game_name)
    if not game_dir:
        abort(404)

    target_game = mapped or game_name
    game_url = url_for("games.play", game_name=target_game, _external=True)
    qr = segno.make(game_url, error="m")

    buffer = io.BytesIO()
    qr.save(
        buffer,
        kind="png",
        scale=10,
        dark="#000000",
        light="#ffffff",
    )
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")


@games_bp.route("/<string:game_name>")
def play_redirect(game_name):
    return redirect(url_for("games.play", game_name=game_name))


@games_bp.route("/<string:game_name>/")
def play(game_name):
    game_dir, mapped = _resolve_game_directory(game_name)
    if not game_dir:
        abort(404)

    if mapped:
        return redirect(url_for("games.play", game_name=mapped))

    index_path = os.path.join(game_dir, "index.html")
    if not os.path.exists(index_path):
        abort(404)

    return send_from_directory(game_dir, "index.html")


@games_bp.route("/<string:game_name>/<path:asset_path>")
def serve_asset(game_name, asset_path):
    game_dir, mapped = _resolve_game_directory(game_name)
    if not game_dir:
        abort(404)
    if mapped:
        return redirect(url_for("games.serve_asset", game_name=mapped, asset_path=asset_path))

    try:
        rel_path = sanitize_asset_path(asset_path)
    except ValueError:
        abort(404)

    full_path = os.path.realpath(os.path.join(game_dir, rel_path))
    base_dir = os.path.realpath(game_dir)
    if not full_path.startswith(base_dir + os.sep) and full_path != base_dir:
        abort(404)
    if not os.path.exists(full_path):
        abort(404)

    return send_from_directory(game_dir, rel_path)
