"""
Application factory.

create_app() wires together config + extensions + blueprints.
Using a factory (rather than a module-level `app = Flask(...)`) is
what lets testing.py spin up an isolated app per test run.

Blueprint registration below is ADDITIVE-ONLY (see Tasks.md merge
strategy) — each person adds their own import + register_blueprint
line as their routes module is built. Never restructure this
function; that's what causes merge conflicts across 4 branches.
"""

from flask import Flask, jsonify

from app.config import config_by_name
from app.extensions import db, bcrypt, jwt, cors


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    cfg = config_by_name[config_name]
    if hasattr(cfg, "validate"):
        cfg.validate()
    app.config.from_object(cfg)

    _init_extensions(app)
    _register_blueprints(app)
    _register_health_check(app)

    # Import models so SQLAlchemy's metadata is complete before anything
    # calls db.create_all() or Alembic autogenerate runs against this app.
    # NOTE: `import app.models` here would rebind the local name `app`
    # to the package itself (shadowing the Flask instance below it),
    # since Python treats a dotted import's first segment as a local
    # assignment target. `from app import models` avoids that trap.
    with app.app_context():
        from app import models  # noqa: F401

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, supports_credentials=True)


def _register_blueprints(app: Flask) -> None:
    # --- Person 1: auth ---
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    # --- Person 2: student ---
    # from app.routes.student import student_bp
    # app.register_blueprint(student_bp, url_prefix="/api/student")

    # --- Person 3: course faculty + class teacher ---
    # from app.routes.faculty import faculty_bp
    # app.register_blueprint(faculty_bp, url_prefix="/api/faculty")
    # from app.routes.class_teacher import class_teacher_bp
    # app.register_blueprint(class_teacher_bp, url_prefix="/api/class-teacher")

    # --- Person 4: health admin + institute admin ---
    # from app.routes.health_admin import health_admin_bp
    # app.register_blueprint(health_admin_bp, url_prefix="/api/health-admin")
    # from app.routes.institute_admin import institute_admin_bp
    # app.register_blueprint(institute_admin_bp, url_prefix="/api/institute-admin")

    pass


def _register_health_check(app: Flask) -> None:
    """Lets you verify the app boots and connects before any real routes exist."""

    @app.get("/api/health")
    def health():
        return jsonify(status="ok"), 200