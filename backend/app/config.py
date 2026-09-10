"""
Environment-based configuration.

Nothing sensitive is hardcoded here — every real value comes from
the environment (see .env.example). The fallback defaults are only
safe for local development against a throwaway DB.
"""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:password@localhost:3306/campustrace",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Recycle connections periodically — avoids "MySQL server has gone away"
    # once the app has been running for a while.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-dev-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_TOKEN_LOCATION = ["headers"]

    # k-anonymity threshold and tracing defaults live in system_config
    # (DB-editable by Institute Admin) — nothing tracing-related belongs here.


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False  # flip to True to log every SQL statement


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "mysql+pymysql://root:password@localhost:3306/campustrace_test",
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    REQUIRED_VARS = ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL")

    @classmethod
    def validate(cls) -> None:
        """Called explicitly from create_app() for prod — never at import
        time, so importing this module never crashes dev/testing just
        because production env vars happen to be unset."""
        missing = [v for v in cls.REQUIRED_VARS if not os.environ.get(v)]
        if missing:
            raise RuntimeError(f"Missing required production env var(s): {', '.join(missing)}")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}