# Corrected app/routes/games.py using current_app.root_path

import os
from flask import Blueprint, render_template, current_app, abort, url_for
from flask_login import login_required # Add if games require login
import jinja2

# Define the blueprint
games_bp = Blueprint('games', __name__, url_prefix='/games')

def get_game_templates():
    """Scans the games template directory for HTML files."""
    games_list = []

    # --- CORRECTED PATH CALCULATION ---
    try:
        # current_app.root_path should be the 'app' directory path
        app_root_path = current_app.root_path
        print(f"DEBUG: current_app.root_path = {app_root_path}")

        # Construct path relative to the app root path
        # app_root/templates/games
        games_template_dir = os.path.join(app_root_path, 'templates', 'games')
        print(f"DEBUG: Calculated path using root_path = {games_template_dir}")

        # Get absolute path for checking (though relative should work now)
        abs_games_template_dir = os.path.abspath(games_template_dir)
        print(f"DEBUG: Calculated absolute path = {abs_games_template_dir}")

        current_working_dir = os.getcwd()
        print(f"DEBUG: Current Working Directory (os.getcwd()) = {current_working_dir}")

    except Exception as e:
        print(f"ERROR getting path details: {e}")
        return games_list
    # --- END CORRECTED PATH CALCULATION ---

    # Check if the directory exists using the (now hopefully correct) path
    dir_exists = os.path.isdir(abs_games_template_dir) # Check absolute path
    # dir_exists = os.path.isdir(games_template_dir) # Or check path relative to app root
    print(f"DEBUG: os.path.isdir('{abs_games_template_dir}') = {dir_exists}")

    if not dir_exists:
        print(f"DEBUG: Games template directory NOT FOUND at: {abs_games_template_dir}")
        # Try listing anyway for debug info
        try:
            print(f"DEBUG: Attempting os.listdir('{abs_games_template_dir}') anyway...")
            items_anyway = os.listdir(abs_games_template_dir)
            print(f"DEBUG: os.listdir *did* return (unexpectedly): {items_anyway}")
        except Exception as e:
            print(f"DEBUG: os.listdir failed as expected: {e}")
        return games_list

    # If directory WAS found:
    print(f"DEBUG: Games template directory FOUND at: {abs_games_template_dir}")
    try:
        all_items = os.listdir(abs_games_template_dir)
        print(f"DEBUG: Items found by os.listdir: {all_items}")

        for item_name in all_items:
            item_path = os.path.join(abs_games_template_dir, item_name)
            # print(f"DEBUG: Checking item: {item_name} at path: {item_path}") # Less verbose now
            if os.path.isfile(item_path) and item_name.lower().endswith('.html') and item_name.lower() != 'index.html':
                print(f"DEBUG: Found valid game template: {item_name}")
                game_name = os.path.splitext(item_name)[0]
                display_name = game_name.replace('_', ' ').replace('-', ' ').title()
                games_list.append({'id': game_name, 'name': display_name})
            # else: print(f"DEBUG: Skipping item: {item_name}") # Less verbose now

        print(f"DEBUG: Finished scanning. Found games: {games_list}")
    except OSError as e:
        print(f"ERROR scanning games directory '{abs_games_template_dir}': {e}")
    except Exception as e:
        print(f"ERROR during game template scanning: {e}")

    return games_list

@games_bp.route('/')
#@login_required
def index():
    """Displays the list of available games."""
    print("--- DEBUG: games.index route called ---")
    available_games = get_game_templates()
    return render_template('games/index.html', games=available_games)

@games_bp.route('/<string:game_name>')
#@login_required
def play(game_name):
    """Renders a specific game template."""
    template_path = f"games/{game_name}.html"
    print(f"DEBUG: Attempting to render game: {template_path}")
    try:
        # Jinja uses paths relative to the *template_folder*, so this should still work
        current_app.jinja_env.get_template(template_path)
        return render_template(template_path, game_title=game_name.replace('_', ' ').title())
    except jinja2.exceptions.TemplateNotFound:
        print(f"DEBUG: Game template not found by Jinja: {template_path}")
        abort(404)
    except Exception as e:
        print(f"ERROR rendering game {game_name}: {e}")
        abort(500)