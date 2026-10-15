import os

from flask import Flask

from . import db, routes


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("TASKLITE_DB", "tasklite.db"),
        API_KEY=os.environ.get("TASKLITE_API_KEY"),
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    app.register_blueprint(routes.bp)
    return app
