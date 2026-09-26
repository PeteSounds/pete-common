"""Shared admin auth for Pete's Flask apps.

Three modes:

  gate  - everything requires admin login except open_paths/open_prefixes.
          Fails closed: refuses to enable without a password.
  open  - everything is public; only routes decorated with @require_admin
          are gated. For apps like LincMadLibs that stay public.
  off   - admin disabled entirely: no gate, @require_admin passes through.
          For dev machines — set via "admin_mode": "off" in fleet.local.json.

Usage:
    from pete_common.admin import enable_admin, require_admin

    enable_admin(app, cfg["admin_password"],
                 open_paths=("/", "/api/health", "/api/vapid-public-key"),
                 open_prefixes=("/static/",),
                 mode="gate")

    @app.route("/api/config", methods=["POST"])
    @require_admin
    def save_config(): ...

Fleet SSO: pass the same sso_secret to every app and sessions share a
`pete_session` cookie at path "/" — one login valid on every app.
"""

import functools
import hmac
import secrets

from markupsafe import Markup

from flask import (
    Blueprint, abort, current_app, jsonify, redirect, render_template_string,
    request, session,
)

SESSION_KEY = "admin"
CSRF_KEY = "csrf"

_LOGIN_HTML = """<!doctype html>
<title>admin</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<body style="margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#16121f;font-family:system-ui">
<form method="post" style="background:#241a3d;padding:2rem 2.4rem;border-radius:14px;color:#f4e9d8;min-width:240px">
  <div style="font-size:1.3rem;margin-bottom:1rem">🔒 admin</div>
  {% if error %}<div style="color:#ff8f8f;margin-bottom:.8rem">{{ error }}</div>{% endif %}
  <input type="hidden" name="next" value="{{ next }}">
  <input type="password" name="password" autofocus placeholder="password"
         style="width:100%;box-sizing:border-box;padding:.7rem;border-radius:8px;border:1px solid #553a80;background:#16121f;color:#f4e9d8">
  <button style="margin-top:1rem;width:100%;padding:.7rem;border:0;border-radius:8px;background:#6b4a9e;color:#fff;font-weight:700">log in</button>
</form>
</body>"""


def _is_open(path: str) -> bool:
    cfg = current_app.extensions["pete_admin"]
    if path == cfg["login_path"] or path.startswith(cfg["login_prefix"]):
        return True
    if path in cfg["open_paths"]:
        return True
    return any(path.startswith(p) for p in cfg["open_prefixes"])


def _safe_next(target) -> str:
    """Only allow local absolute paths — kills open redirects."""
    if isinstance(target, str) and target.startswith("/") and not target.startswith("//"):
        return target
    return "/"


def _wants_json() -> bool:
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def _deny():
    if _wants_json():
        return jsonify({"error": "admin login required"}), 401
    cfg = current_app.extensions["pete_admin"]
    return redirect(f"{cfg['base_path']}{cfg['login_path']}?next={request.path}")


def require_admin(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        cfg = current_app.extensions.get("pete_admin", {})
        if not cfg.get("disabled") and not session.get(SESSION_KEY):
            return _deny()
        return fn(*args, **kwargs)
    return wrapper


def csrf_token() -> str:
    token = session.get(CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(24)
        session[CSRF_KEY] = token
    return token


def csrf_field() -> Markup:
    return Markup(f'<input type="hidden" name="csrf" value="{csrf_token()}">')


def csrf_protect(fn):
    """For admin form POSTs: reject submissions without a valid csrf field."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if request.method == "POST" and not hmac.compare_digest(
            request.form.get("csrf", ""), session.get(CSRF_KEY, "")
        ):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def _make_blueprint(password: str, login_path: str) -> Blueprint:
    bp = Blueprint("pete_admin", __name__)

    @bp.route(login_path, methods=["GET", "POST"])
    def login():
        cfg = current_app.extensions["pete_admin"]
        bp_path = cfg["base_path"]
        nxt = _safe_next(request.values.get("next"))
        if request.method == "POST":
            if password and hmac.compare_digest(request.form.get("password", ""), password):
                session[SESSION_KEY] = True
                session.permanent = True
                return redirect(f"{bp_path}{nxt}")
            return render_template_string(_LOGIN_HTML, error="nope", next=nxt), 401
        return render_template_string(_LOGIN_HTML, error=None, next=nxt)

    @bp.route(f"{login_path}/out")
    def logout():
        session.pop(SESSION_KEY, None)
        cfg = current_app.extensions["pete_admin"]
        return redirect(f"{cfg['base_path']}{login_path}")

    return bp


def enable_admin(app, password=None, *, open_paths=(), open_prefixes=(),
                 mode="gate", login_path="/admin/login", base_path="",
                 sso_secret=None, secure_cookies=None):
    """Install admin auth on a Flask app. See module docstring."""
    if mode not in ("gate", "open", "off"):
        raise ValueError(f"bad admin mode: {mode!r}")
    if mode == "gate" and not password:
        raise RuntimeError("admin gate mode requires a password — refusing to run open")

    app.extensions["pete_admin"] = {
        "login_path": login_path,
        "login_prefix": login_path + "/",
        "base_path": base_path.rstrip("/"),
        "open_paths": set(open_paths),
        "open_prefixes": tuple(open_prefixes),
        "disabled": mode == "off",
    }

    # Cookie hardening + optional fleet SSO.
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    if secure_cookies is None:
        secure_cookies = not app.debug
    app.config["SESSION_COOKIE_SECURE"] = secure_cookies
    if sso_secret:
        app.secret_key = sso_secret
        app.config["SESSION_COOKIE_NAME"] = "pete_session"
        app.config["SESSION_COOKIE_PATH"] = "/"

    app.register_blueprint(_make_blueprint(password, login_path))
    app.jinja_env.globals["csrf_field"] = csrf_field

    if mode == "gate":
        @app.before_request
        def _pete_admin_gate():
            if request.method == "OPTIONS" or _is_open(request.path):
                return None
            if not session.get(SESSION_KEY):
                return _deny()
            return None
