import logging
import sys
import os
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from .config import Config
from jinja2 import TemplateNotFound
from werkzeug.exceptions import HTTPException

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def configure_logging(app):
    """Configure application logging to stream detailed diagnostics."""

    log_level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
    )

    gunicorn_error_logger = logging.getLogger("gunicorn.error")
    handlers = []

    if gunicorn_error_logger.handlers:
        handlers = list(gunicorn_error_logger.handlers)
    else:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        handlers = [stream_handler]

    def _handler_targets_console(handler):
        if isinstance(handler, logging.StreamHandler):
            target_stream = getattr(handler, "stream", None)
            if target_stream in (sys.stdout, sys.stderr):
                return True
            try:
                target_fileno = target_stream.fileno()
            except Exception:
                target_fileno = None

            if target_fileno is not None:
                stdout_fileno = None
                stderr_fileno = None
                try:
                    stdout_fileno = sys.stdout.fileno()
                except Exception:
                    stdout_fileno = None
                try:
                    stderr_fileno = sys.stderr.fileno()
                except Exception:
                    stderr_fileno = None
                return target_fileno in {stdout_fileno, stderr_fileno}
        return False

    has_console_handler = any(_handler_targets_console(handler) for handler in handlers)

    if not has_console_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        handlers.append(console_handler)

    app.logger.handlers = []
    for handler in handlers:
        handler.setLevel(log_level)
        if handler.formatter is None:
            handler.setFormatter(formatter)
        if handler not in app.logger.handlers:
            app.logger.addHandler(handler)

    app.logger.setLevel(log_level)
    app.logger.propagate = False

    root_logger = logging.getLogger()
    root_logger.handlers = []
    for handler in handlers:
        if handler not in root_logger.handlers:
            root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    gunicorn_access_logger = logging.getLogger("gunicorn.access")
    for handler in handlers:
        if handler not in gunicorn_access_logger.handlers:
            gunicorn_access_logger.addHandler(handler)

    for handler in gunicorn_access_logger.handlers:
        handler.setLevel(log_level)
        if handler.formatter is None:
            handler.setFormatter(formatter)
    gunicorn_access_logger.setLevel(log_level)

    app.logger.debug(
        "Logging configured. Active level: %s",
        logging.getLevelName(log_level),
    )


def create_app(config_overrides=None):
    instance_path = None
    if config_overrides:
        instance_path = config_overrides.get("INSTANCE_PATH")
    app = Flask(__name__, instance_path=instance_path)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    os.makedirs(app.instance_path, exist_ok=True)

    configure_logging(app)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Import models
    from . import models

    # Register Blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.tests import tests_bp
    from .routes.vocabulary import vocab_bp
    from .routes.admin import admin_bp
    from .routes.reading import reading_bp
    from .routes.games import games_bp
    from .games_storage import migrate_legacy_games

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tests_bp)
    app.register_blueprint(vocab_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reading_bp)
    app.register_blueprint(games_bp)

    # Set up Login Manager
    login_manager.login_view = 'auth.login'

    # Error handlers and request logging
    from flask_wtf.csrf import CSRFError

    @app.before_request
    def log_request():
        app.logger.debug("Handling request %s %s", request.method, request.path)

    @app.after_request
    def log_response(response):
        status = response.status_code
        if status >= 500:
            app.logger.error(
                "Server error response %s for %s %s",
                status,
                request.method,
                request.path,
            )
        elif status >= 400:
            app.logger.warning(
                "Client error response %s for %s %s",
                status,
                request.method,
                request.path,
            )
        else:
            app.logger.debug(
                "Completed request %s %s with status %s",
                request.method,
                request.path,
                status,
            )
        return response

    @app.errorhandler(403)
    def forbidden(e):
        app.logger.warning(
            "Forbidden access attempted on %s %s: %s",
            request.method,
            request.path,
            e,
        )
        try:
            return render_template('errors/403.html'), 403
        except TemplateNotFound:
            return "Forbidden", 403

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning(
            "CSRF error on %s %s: %s",
            request.method,
            request.path,
            e.description,
        )
        try:
            return render_template('errors/csrf_error.html', reason=e.description), 400
        except TemplateNotFound:
            return f"CSRF Error: {e.description}", 400

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        if isinstance(e, HTTPException):
            if e.code >= 500:
                app.logger.exception("HTTP exception triggered: %s", e)
            return e

        app.logger.exception("Unhandled exception encountered")
        try:
            return render_template('errors/500.html'), 500
        except TemplateNotFound:
            return "Internal Server Error", 500

    # Context processor to inject csrf_token into all templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf())

    with app.app_context():
        migrate_legacy_games(app)

    return app
