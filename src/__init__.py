from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flasgger import Swagger

_db = SQLAlchemy()
db = _db
migrate = Migrate()
swagger = Swagger()


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config.Config')

    _db.init_app(app)
    migrate.init_app(app, _db)
    swagger.init_app(app)

    # Настройка Celery
    from src.extensions import celery
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    from src.routes.auth import auth_bp
    from src.routes.web import web_bp
    from src.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    from src.decorators import current_user
    @app.context_processor
    def inject_user():
        return {'current_user': current_user()}

    from src.utils.errors import register_error_handlers
    register_error_handlers(app)

    return app