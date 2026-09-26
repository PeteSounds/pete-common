import json

from pete_common.config import load_shared


def write_fleet(tmp_path, data):
    (tmp_path / "fleet.json").write_text(json.dumps(data))


def test_missing_file_returns_empty(tmp_path):
    app_dir = tmp_path / "myapp"
    app_dir.mkdir()
    assert load_shared(app_dir) == {}


def test_shared_values_and_per_app_override(tmp_path):
    write_fleet(tmp_path, {
        "admin_password": "pw",
        "sso_secret": "abc",
        "apps": {"petepills": {"base_path": "/pills"}},
    })
    app_dir = tmp_path / "petepills"
    app_dir.mkdir()
    cfg = load_shared(app_dir, "petepills")
    assert cfg["admin_password"] == "pw"
    assert cfg["sso_secret"] == "abc"
    assert cfg["base_path"] == "/pills"
    assert "apps" not in cfg


def test_other_apps_see_shared_only(tmp_path):
    write_fleet(tmp_path, {
        "admin_password": "pw",
        "apps": {"petepills": {"base_path": "/pills"}},
    })
    app_dir = tmp_path / "lincmadlibs"
    app_dir.mkdir()
    cfg = load_shared(app_dir, "lincmadlibs")
    assert cfg == {"admin_password": "pw"}


def test_corrupt_file_returns_empty(tmp_path):
    (tmp_path / "fleet.json").write_text("{not json")
    app_dir = tmp_path / "myapp"
    app_dir.mkdir()
    assert load_shared(app_dir) == {}

import json

from pete_common.config import load_shared


def write_fleet(tmp_path, data):
    (tmp_path / "fleet.json").write_text(json.dumps(data))


def test_missing_file_returns_empty(tmp_path):
    app_dir = tmp_path / "myapp"
    app_dir.mkdir()
    assert load_shared(app_dir) == {}


def test_shared_values_and_per_app_override(tmp_path):
    write_fleet(tmp_path, {
        "admin_password": "pw",
        "sso_secret": "abc",
        "apps": {"petepills": {"base_path": "/pills"}},
    })
    app_dir = tmp_path / "petepills"
    app_dir.mkdir()
    cfg = load_shared(app_dir, "petepills")
    assert cfg["admin_password"] == "pw"
    assert cfg["sso_secret"] == "abc"
    assert cfg["base_path"] == "/pills"
    assert "apps" not in cfg


def test_other_apps_see_shared_only(tmp_path):
    write_fleet(tmp_path, {
        "admin_password": "pw",
        "apps": {"petepills": {"base_path": "/pills"}},
    })
    app_dir = tmp_path / "lincmadlibs"
    app_dir.mkdir()
    cfg = load_shared(app_dir, "lincmadlibs")
    assert cfg == {"admin_password": "pw"}


def test_corrupt_file_returns_empty(tmp_path):
    (tmp_path / "fleet.json").write_text("{not json")
    app_dir = tmp_path / "myapp"
    app_dir.mkdir()
    assert load_shared(app_dir) == {}


def test_fleet_local_json_merges_and_wins(tmp_path):
    write_fleet(tmp_path, {"admin_password": "pw", "sso_secret": "abc"})
    (tmp_path / "fleet.local.json").write_text('{"admin_mode": "off"}')
    app_dir = tmp_path / "myapp"
    app_dir.mkdir()
    cfg = load_shared(app_dir, "myapp")
    assert cfg == {"admin_password": "pw", "sso_secret": "abc", "admin_mode": "off"}
