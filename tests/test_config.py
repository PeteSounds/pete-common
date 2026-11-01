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


# --- env overrides for load_shared ---------------------------------------

def test_fleet_env_override(tmp_path, monkeypatch):
    write_fleet(tmp_path, {"admin_mode": "gate"})
    app_dir = tmp_path / "x"
    app_dir.mkdir()
    monkeypatch.setenv("PETE_FLEET_ADMIN_MODE", "off")
    assert load_shared(app_dir)["admin_mode"] == "off"


# --- load_config ----------------------------------------------------------

import pytest

from pete_common.config import deep_merge, load_config


def test_load_config_missing_is_empty(tmp_path):
    assert load_config(tmp_path) == {}


def test_load_config_prefers_config_over_example(tmp_path):
    (tmp_path / "config.json").write_text('{"a": 1}')
    (tmp_path / "config.example.json").write_text('{"a": 2, "b": 2}')
    assert load_config(tmp_path) == {"a": 1}


def test_load_config_example_fallback_and_local_overlay(tmp_path):
    (tmp_path / "config.example.json").write_text('{"app": {"port": 1, "name": "x"}}')
    (tmp_path / "config.local.json").write_text('{"app": {"port": 2}}')
    assert load_config(tmp_path) == {"app": {"port": 2, "name": "x"}}


def test_load_config_env_overrides(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text('{"app": {"port": 1}}')
    monkeypatch.setenv("MYAPP_APP_PORT", "5059")
    monkeypatch.setenv("MYAPP_APP_DEBUG", "true")
    monkeypatch.setenv("MYAPP_MODEL_EDGE_THRESHOLD", "0.5")
    monkeypatch.setenv("MYAPP_NOSECTION", "ignored")
    cfg = load_config(tmp_path, env_prefix="MYAPP")
    assert cfg == {"app": {"port": 5059, "debug": True},
                   "model": {"edge_threshold": 0.5}}


def test_load_config_malformed_raises(tmp_path):
    (tmp_path / "config.json").write_text("{nope")
    with pytest.raises(ValueError):
        load_config(tmp_path)


def test_deep_merge_replaces_non_dicts():
    assert deep_merge({"a": {"b": 1}, "c": 1}, {"a": 5, "c": {"d": 1}}) == {"a": 5, "c": {"d": 1}}
