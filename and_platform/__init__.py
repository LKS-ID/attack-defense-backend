from dotenv import load_dotenv

load_dotenv()

from and_platform.models import Teams, db, migrate
from and_platform.api import api_blueprint
from and_platform.core.config import get_config, set_config
from and_platform.checker import CheckerExecutor
from and_platform.checker.utils import install_checker_dependencies
from and_platform.cache import cache
from and_platform.socket import socketio
from celery import Celery, Task
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from pathlib import Path

import datetime
import os
import sqlalchemy


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                db.engine.dispose()
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.Task = FlaskTask
    celery_app.set_default()
    celery_app.conf.update(
        flask_func=create_app,
        beat_schedule_filename="/tmp/celerybeat-schedule",
        beat_max_loop_interval=5,
    )

    app.extensions["celery"] = celery_app
    return celery_app


def setup_jwt_app(app: Flask):
    jwt = JWTManager(app)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return db.session.execute(
            sqlalchemy.select(Teams).filter(Teams.id == identity["team"]["id"])
        ).scalar()


def init_data_dir(app):
    app.config["TEMPLATE_DIR"] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates"
    )
    if not app.config.get("DATA_DIR"):
        app.config["DATA_DIR"] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".adce_data"
        )

    for d in ["challenges", "services", "vpn", "vpn-zip"]:
        dirpath = os.path.join(app.config["DATA_DIR"], d)
        os.makedirs(dirpath, exist_ok=True)


def load_adce_config():
    # If config already exists in database, it will not follow .env
    for key, value in os.environ.items():
        realkey = key[5:]
        if not key.startswith("ADCE_") or get_config(realkey) != None:
            continue
        set_config(realkey, value)


def create_app():
    app = Flask(
        __name__,
        static_url_path="/static",
        static_folder="static",
    )

    with app.app_context():
        app.config.from_prefixed_env()
        redis_uri = app.config.get("REDIS_URI", os.getenv("REDIS_URI"))
        app.config.from_mapping(
            CELERY=dict(
                broker_url=redis_uri,
                broker_connection_retry_on_startup=True,
                result_backend=redis_uri,
                task_ignore_result=True,
            ),
        )

        # Extensions
        CORS(
            app,
            origins=[
                "http://127.0.0.1:3000",
                "http://localhost:3000",
                "http://localhost",
                "https://and.idcyberskills.com",
                "https://mirror-and-frontend-4z190z51p-boncengs-projects.vercel.app",
            ],
        )
        
        db.init_app(app)
        migrate.init_app(app, db)
        cache.init_app(app)
        socketio.init_app(app)
        
        app.config["JWT_SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
        app.config["JWT_ALGORITHM"] = "HS512"
        app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=12)
        setup_jwt_app(app)

        try:
            load_adce_config()
            init_data_dir(app)
        except sqlalchemy.exc.ProgrammingError:
            # To detect that the relation has not been created yet
            app.logger.warning("Error calling some function while create_app")

        # Blueprints
        app.register_blueprint(api_blueprint)
        
    return app


def create_celery(flask_app: Flask | None = None) -> Celery:
    if flask_app == None:
        flask_app = create_app()
    return celery_init_app(flask_app)


def create_checker():
    celery = create_celery()
    celery.conf.update(
        include=["and_platform.checker.tasks"],
        task_default_queue="checker",
    )
    return celery


def create_checker_executor():
    app = create_app()
    with app.app_context():
        install_checker_dependencies()
        return CheckerExecutor(app)


def create_contest_worker(flask_app: Flask):
    celery = create_celery(create_app())
    celery.conf.update(
        include=["and_platform.core.contest", "and_platform.core.service", "and_platform.core.server"],
        task_default_queue="contest",
    )
    return celery


def create_scheduler(flask_app: Flask):
    from and_platform.core.contest import install_contest_entries

    with flask_app.app_context():
        celery = create_celery(flask_app)
        celery.conf.beat_schedule = {
            "contest.start": {
                "task": "and_platform.core.contest.init_contest",
                "schedule": 10,
                "options": {
                    "queue": "contest",
                },
            },
        }

        install_contest_entries(celery)

        return celery
