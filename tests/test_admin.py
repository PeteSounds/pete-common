import pytest
from flask import Flask, jsonify

from pete_common.admin import csrf_protect, enable_admin, require_admin


def make_app(mode="gate", password="pw", **kw):
    app = Flask(__name__)
    app.secret_key = "test"
    app.config["TESTING"] = True

    enable_admin(app, password, mode=mode, secure_cookies=False,
                 open_paths=("/", "/api/health"), open_prefixes=("/static/",), **kw)

    @app.route("/")
    def index():
        return "home"

    @app.route("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.route("/static/style.css")
    def style():
        return "css"

    @app.route("/admin/panel")
    def panel():
        return "panel"

    @app.route("/api/secret", methods=["POST"])
    @require_admin
    def secret():
        return jsonify({"ok": True})

    @app.route("/admin/form", methods=["GET", "POST"])
    @require_admin
    @csrf_protect
    def form():
        return "form"

    return app


def login(client, path="/"):
    return client.post("/admin/login", data={"password": "pw", "next": path})


# --- gate mode ---

def test_gate_blocks_everything_by_default():
    c = make_app().test_client()
    assert c.get("/admin/panel").status_code == 302  # redirect to login
    assert c.post("/api/secret").status_code == 401


def test_gate_respects_open_paths_and_prefixes():
    c = make_app().test_client()
    assert c.get("/").status_code == 200
    assert c.get("/api/health").get_json()["ok"] is True
    assert c.get("/static/style.css").status_code == 200


def test_gate_login_then_access():
    c = make_app().test_client()
    r = login(c, "/admin/panel")
    assert r.status_code == 302 and r.headers["Location"] == "/admin/panel"
    assert c.get("/admin/panel").status_code == 200
    assert c.post("/api/secret").get_json()["ok"] is True


def test_gate_wrong_password():
    c = make_app().test_client()
    r = c.post("/admin/login", data={"password": "wrong"})
    assert r.status_code == 401
    assert c.get("/admin/panel").status_code == 302


def test_gate_refuses_to_enable_without_password():
    with pytest.raises(RuntimeError):
        make_app(password=None)


# --- open mode ---

def test_open_mode_leaves_routes_public():
    c = make_app(mode="open").test_client()
    assert c.get("/admin/panel").status_code == 200  # undecorated = public


def test_open_mode_require_admin_api_gets_401_json():
    r = make_app(mode="open").test_client().post("/api/secret")
    assert r.status_code == 401
    assert r.get_json()["error"]


def test_open_mode_login_then_access():
    c = make_app(mode="open").test_client()
    login(c)
    assert c.post("/api/secret").get_json()["ok"] is True


# --- off mode (dev machines: no gate, require_admin passes through) ---

def test_off_mode_everything_public():
    c = make_app(mode="off").test_client()
    assert c.get("/admin/panel").status_code == 200
    assert c.post("/api/secret").get_json()["ok"] is True  # decorated route open too


# --- next sanitization / logout / csrf ---

def test_next_param_cannot_leave_the_site():
    c = make_app().test_client()
    r = c.post("/admin/login", data={"password": "pw", "next": "https://evil.example/x"})
    assert r.headers["Location"] == "/"
    r = c.post("/admin/login", data={"password": "pw", "next": "//evil.example"})
    assert r.headers["Location"] == "/"


def test_logout():
    c = make_app().test_client()
    login(c)
    c.get("/admin/login/out")
    assert c.get("/admin/panel").status_code == 302


def test_base_path_prefixes_redirects():
    """Behind Caddy's /pills subpath the app sees stripped paths — login
    redirects must re-add the prefix or they land off-app (404)."""
    c = make_app(base_path="/pills").test_client()
    r = c.get("/admin/panel")
    assert r.headers["Location"] == "/pills/admin/login?next=/admin/panel"
    r = c.post("/admin/login", data={"password": "pw", "next": "/admin/panel"})
    assert r.headers["Location"] == "/pills/admin/panel"


def test_csrf_protect_rejects_bad_token():
    c = make_app().test_client()
    login(c)
    assert c.post("/admin/form", data={"csrf": "bogus"}).status_code == 403
    with c.session_transaction() as s:
        s["csrf"] = "tok123"
    assert c.post("/admin/form", data={"csrf": "tok123"}).status_code == 200
