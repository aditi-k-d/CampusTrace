"""
Role-based access control.

@role_required("health_admin", "institute_admin") is how every
downstream route (Person 2/3/4's modules) gates access — it reads the
role out of the JWT claims, never trusts a role passed in the request
body, so a student can't just say {"role": "institute_admin"} and get in.
"""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def role_required(*allowed_roles):
    """Route decorator: requires a valid JWT AND a role in allowed_roles.
    Usage: @role_required("health_admin", "institute_admin")"""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if role not in allowed_roles:
                return (
                    jsonify(error=f"Forbidden: requires role in {list(allowed_roles)}"),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_user_role() -> str | None:
    """Returns the caller's role if a valid JWT is present, else None.
    Never raises — for endpoints (like /auth/register) that behave
    differently depending on whether the caller is authenticated,
    without making auth mandatory."""

    verify_jwt_in_request(optional=True)
    claims = get_jwt()
    return claims.get("role") if claims else None