import logging

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from openbrokerapi import api as openbrokerapi

from . import log_util
from .config import config

log_util.configure(logging.root, log_level="INFO")
logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()


def create_app(env: str = "prod"):
    # We need to import models, even though it's unused, in order to enable
    # `flask db migrate`
    from broker import models  # noqa: F401
    from broker.api import API

    app = Flask(__name__)
    app.config.from_object(config[env])

    db.init_app(app)
    migrate.init_app(app, db)

    credentials = openbrokerapi.BrokerCredentials(
        app.config["BROKER_USERNAME"], app.config["BROKER_PASSWORD"]
    )

    app.register_blueprint(openbrokerapi.get_blueprint(API(), credentials, logger))

    # Endpoint to test if server comes up
    @app.route("/ping")
    def ping():
        return "PONG"

    return app
