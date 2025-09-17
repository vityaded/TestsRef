import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
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
    from. routes.reading import reading_bp
    from .routes.games import games_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tests_bp)
    app.register_blueprint(vocab_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reading_bp)
    app.register_blueprint(games_bp)

    # Set up Login Manager
    login_manager.login_view = 'auth.login'

    # Error handlers
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('errors/csrf_error.html', reason=e.description), 400

    # Context processor to inject csrf_token into all templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf())

    return app
