"""The app module, containing the app factory function."""
import logging
import sys

from flask import Flask

from editor import bot, main, pecha, user
from editor.extensions import db, github_oauth, migrate


def create_app(config_object="editor.settings"):
    """Create application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/. """
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_shellcontext(app)
    return app


def register_extensions(app):
    """Register Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    github_oauth.init_app(app)


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(user.views.blueprint)
    app.register_blueprint(pecha.views.blueprint)
    app.register_blueprint(main.views.blueprint)
    app.register_blueprint(bot.views.blueprint)


def register_shellcontext(app):
    """Register shell context objects."""

    def shell_context():
        """Shell context objects."""
        return {"db": db, "User": user.models.User, "Pecha": pecha.models.Pecha}

    app.shell_context_processor(shell_context)


def configure_logger(app):
    """Configure loggers."""
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)
