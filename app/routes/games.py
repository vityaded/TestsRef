# Corrected app/routes/games.py using current_app.root_path

import io
import os

import jinja2
import segno
from flask import (
    Blueprint,
    render_template,
    current_app,
    abort,
    url_for,
    flash,
    redirect,
    request,
    send_file,
)
from flask_login import login_required  # Add if games require login
from werkzeug.utils import secure_filename

from app.forms import AddGameForm, EditGameForm

# Define the blueprint
games_bp = Blueprint('games', __name__, url_prefix='/games')

def get_game_templates():
    """Scans the games template directory for HTML files."""
    games_list = []

    # --- CORRECTED PATH CALCULATION ---
    logger = current_app.logger

    try:
        # current_app.root_path should be the 'app' directory path
        app_root_path = current_app.root_path
        logger.debug("games.get_game_templates: current_app.root_path=%s", app_root_path)

        # Construct path relative to the app root path
        # app_root/templates/games
        games_template_dir = os.path.join(app_root_path, 'templates', 'games')
        logger.debug(
            "games.get_game_templates: calculated games template dir=%s",
            games_template_dir,
        )

        # Get absolute path for checking (though relative should work now)
        abs_games_template_dir = os.path.abspath(games_template_dir)
        logger.debug(
            "games.get_game_templates: absolute games template dir=%s",
            abs_games_template_dir,
        )

        current_working_dir = os.getcwd()
        logger.debug(
            "games.get_game_templates: current working directory=%s",
            current_working_dir,
        )

    except Exception:  # pragma: no cover - defensive logging
        logger.exception("games.get_game_templates: error while computing paths")
        return games_list
    # --- END CORRECTED PATH CALCULATION ---

    # Check if the directory exists using the (now hopefully correct) path
    dir_exists = os.path.isdir(abs_games_template_dir) # Check absolute path
    # dir_exists = os.path.isdir(games_template_dir) # Or check path relative to app root
    logger.debug(
        "games.get_game_templates: os.path.isdir(%s)=%s",
        abs_games_template_dir,
        dir_exists,
    )

    if not dir_exists:
        logger.warning(
            "games.get_game_templates: games template directory not found at %s",
            abs_games_template_dir,
        )
        # Try listing anyway for debug info
        try:
            logger.debug(
                "games.get_game_templates: attempting os.listdir(%s)", abs_games_template_dir
            )
            items_anyway = os.listdir(abs_games_template_dir)
            logger.debug(
                "games.get_game_templates: unexpected os.listdir result: %s",
                items_anyway,
            )
        except Exception:  # pragma: no cover - defensive logging
            logger.exception(
                "games.get_game_templates: os.listdir failed for %s",
                abs_games_template_dir,
            )
        return games_list

    # If directory WAS found:
    logger.debug(
        "games.get_game_templates: games template directory found at %s",
        abs_games_template_dir,
    )
    try:
        all_items = os.listdir(abs_games_template_dir)
        logger.debug(
            "games.get_game_templates: os.listdir returned %s",
            all_items,
        )

        for item_name in all_items:
            item_path = os.path.join(abs_games_template_dir, item_name)
            # print(f"DEBUG: Checking item: {item_name} at path: {item_path}") # Less verbose now
            if os.path.isfile(item_path) and item_name.lower().endswith('.html') and item_name.lower() != 'index.html':
                logger.debug(
                    "games.get_game_templates: found valid game template %s",
                    item_name,
                )
                game_name = os.path.splitext(item_name)[0]
                display_name = game_name.replace('_', ' ').replace('-', ' ').title()
                games_list.append({'id': game_name, 'name': display_name})
            # else: print(f"DEBUG: Skipping item: {item_name}") # Less verbose now

        logger.debug(
            "games.get_game_templates: finished scanning; found games=%s",
            games_list,
        )
    except OSError:
        logger.exception(
            "games.get_game_templates: OS error while scanning %s",
            abs_games_template_dir,
        )
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("games.get_game_templates: unexpected error while scanning")

    return games_list

@games_bp.route('/')
#@login_required
def index():
    """Displays the list of available games."""
    current_app.logger.debug("games.index: route called")
    available_games = get_game_templates()
    form = AddGameForm()
    return render_template('games/index.html', games=available_games, form=form)

@games_bp.route('/add', methods=['POST'])
@login_required
def add_game():
    """Creates a new game template from the provided HTML content."""
    form = AddGameForm()

    if form.validate_on_submit():
        game_name = form.name.data.strip()
        html_content = form.content.data
        sanitized_name = secure_filename(game_name).lower()

        if not sanitized_name:
            flash('Invalid game name. Please use letters, numbers, or underscores.', 'danger')
            return redirect(url_for('games.index'))

        file_name = f"{sanitized_name}.html"
        games_dir = os.path.join(current_app.root_path, 'templates', 'games')
        os.makedirs(games_dir, exist_ok=True)
        file_path = os.path.join(games_dir, file_name)

        if os.path.exists(file_path):
            flash('A game with this name already exists. Please choose another name.', 'danger')
            return redirect(url_for('games.index'))

        try:
            with open(file_path, 'w', encoding='utf-8') as game_file:
                game_file.write(html_content)
        except OSError as exc:
            current_app.logger.exception('Failed to create game template %s: %s', file_name, exc)
            flash('Could not save the game. Please try again later.', 'danger')
        else:
            flash('Game added successfully!', 'success')
            return redirect(url_for('games.play', game_name=sanitized_name))

    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')

    return redirect(url_for('games.index'))


def _get_game_file_path(game_name: str) -> str:
    games_dir = os.path.join(current_app.root_path, 'templates', 'games')
    return os.path.join(games_dir, f"{game_name}.html")


@games_bp.route('/edit/<string:game_name>', methods=['GET', 'POST'])
@login_required
def edit_game(game_name):
    """Updates an existing game template and optionally renames it."""
    file_path = _get_game_file_path(game_name)

    if not os.path.exists(file_path):
        abort(404)

    form = EditGameForm()

    if request.method == 'GET':
        try:
            with open(file_path, 'r', encoding='utf-8') as game_file:
                form.name.data = game_name
                form.content.data = game_file.read()
        except OSError:
            current_app.logger.exception(
                'Failed to read game template %s for editing', file_path
            )
            flash('Could not load the game for editing. Please try again later.', 'danger')
            return redirect(url_for('games.index'))

    if form.validate_on_submit():
        new_name = form.name.data.strip()
        sanitized_name = secure_filename(new_name).lower()

        if not sanitized_name:
            flash('Invalid game name. Please use letters, numbers, or underscores.', 'danger')
            return render_template('games/edit_game.html', form=form, original_game_name=game_name)

        new_file_path = _get_game_file_path(sanitized_name)

        if sanitized_name != game_name and os.path.exists(new_file_path):
            flash('A game with this name already exists. Please choose another name.', 'danger')
            return render_template('games/edit_game.html', form=form, original_game_name=game_name)

        try:
            target_path = new_file_path if sanitized_name != game_name else file_path
            with open(target_path, 'w', encoding='utf-8') as game_file:
                game_file.write(form.content.data)

            if sanitized_name != game_name:
                os.remove(file_path)
        except OSError as exc:
            current_app.logger.exception('Failed to update game template %s: %s', file_path, exc)
            if sanitized_name != game_name and os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except OSError:
                    current_app.logger.exception(
                        'Failed to remove partially written game template %s', target_path
                    )
            flash('Could not save the game. Please try again later.', 'danger')
            return render_template('games/edit_game.html', form=form, original_game_name=game_name)

        flash('Game updated successfully!', 'success')
        return redirect(url_for('games.play', game_name=sanitized_name))

    if request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')

    return render_template('games/edit_game.html', form=form, original_game_name=game_name)


@games_bp.route('/delete/<string:game_name>', methods=['POST'])
@login_required
def delete_game(game_name):
    """Deletes a saved game template."""
    file_path = _get_game_file_path(game_name)

    if not os.path.exists(file_path):
        abort(404)

    try:
        os.remove(file_path)
    except OSError:
        current_app.logger.exception('Failed to delete game template %s', file_path)
        flash('Could not delete the game. Please try again later.', 'danger')
    else:
        flash('Game deleted successfully.', 'success')

    return redirect(url_for('games.index'))


@games_bp.route('/<string:game_name>/qr.png')
def game_qr_code(game_name: str):
    """Generates a QR code image for the requested game."""
    file_path = _get_game_file_path(game_name)

    if not os.path.exists(file_path):
        abort(404)

    game_url = url_for('games.play', game_name=game_name, _external=True)
    qr = segno.make(game_url, error='m')

    buffer = io.BytesIO()
    qr.save(
        buffer,
        kind='png',
        scale=10,
        dark='#000000',
        light='#ffffff',
    )
    buffer.seek(0)

    return send_file(buffer, mimetype='image/png')


@games_bp.route('/<string:game_name>')
#@login_required
def play(game_name):
    """Renders a specific game template."""
    template_path = f"games/{game_name}.html"
    current_app.logger.debug(
        "games.play: attempting to render template %s",
        template_path,
    )
    try:
        # Jinja uses paths relative to the *template_folder*, so this should still work
        current_app.jinja_env.get_template(template_path)
        return render_template(template_path, game_title=game_name.replace('_', ' ').title())
    except jinja2.exceptions.TemplateNotFound:
        current_app.logger.warning(
            "games.play: game template not found: %s",
            template_path,
        )
        abort(404)
    except Exception as e:
        current_app.logger.exception("games.play: error rendering game %s", game_name)
        abort(500)
