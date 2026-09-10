"""
Central place for Flask extension instances.

Every module (models, routes, services) should import db/bcrypt/jwt
from here rather than instantiating its own — this avoids circular
imports between app/__init__.py and everything that needs the db.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
cors = CORS()