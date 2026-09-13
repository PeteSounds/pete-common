import json
import os

from pete_common.jsonio import load_json, write_json


def test_round_trip(tmp_path):
    p = tmp_path / "x.json"
    write_json(p, {"a": 1, "emoji": "☕"})
    assert load_json(p) == {"a": 1, "emoji": "☕"}


def test_load_missing_returns_default(tmp_path):
    assert load_json(tmp_path / "nope.json", default=[]) == []


def test_no_tmp_litter(tmp_path):
    p = tmp_path / "x.json"
    write_json(p, {"a": 1})
    assert os.listdir(tmp_path) == ["x.json"]


def test_unicode_modes_load_the_same(tmp_path):
    for flag in (True, False):
        p = tmp_path / f"x{flag}.json"
        write_json(p, {"emoji": "☕"}, ensure_ascii=flag)
        assert json.loads(p.read_text())["emoji"] == "☕"
