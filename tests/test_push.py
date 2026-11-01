import json
import sys
import types

import pytest

from pete_common import push


def test_load_vapid_explicit_wins(tmp_path):
    assert push.load_vapid(tmp_path / "missing.json", "p", "q") == ("p", "q")


def test_load_vapid_file_formats(tmp_path):
    f = tmp_path / "vapid.json"
    f.write_text(json.dumps({"private_base64url": "a", "public_base64url": "b"}))
    assert push.load_vapid(f) == ("a", "b")
    f.write_text(json.dumps({"private_key": "c", "public_key": "d"}))
    assert push.load_vapid(f) == ("c", "d")
    f.write_text("{bad")
    assert push.load_vapid(f) == (None, None)
    assert push.load_vapid(tmp_path / "missing.json") == (None, None)


class FakeError(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}")
        self.response = types.SimpleNamespace(status_code=status)


@pytest.fixture
def fake_webpush(monkeypatch):
    calls = []
    behaviour = {}

    def webpush(**kwargs):
        calls.append(kwargs)
        status = behaviour.get(kwargs["subscription_info"]["endpoint"])
        if status:
            raise FakeError(status)

    monkeypatch.setitem(sys.modules, "pywebpush", types.SimpleNamespace(webpush=webpush))
    return calls, behaviour


def test_send_ok_sets_audience(fake_webpush):
    calls, _ = fake_webpush
    sub = {"endpoint": "https://push.example.com/abc"}
    assert push.send(sub, {"t": 1}, "priv", "mailto:x@y") == push.SENT
    assert calls[0]["vapid_claims"] == {"sub": "mailto:x@y", "aud": "https://push.example.com"}
    assert calls[0]["data"] == '{"t": 1}'


def test_send_without_key_fails_fast(fake_webpush):
    calls, _ = fake_webpush
    assert push.send({"endpoint": "https://a/b"}, {}, None, "s") == push.FAILED
    assert calls == []


def test_send_all_classifies(fake_webpush):
    _, behaviour = fake_webpush
    behaviour.update({"https://a/gone": 410, "https://a/missing": 404, "https://a/err": 500})
    subs = [{"endpoint": e} for e in ("https://a/ok", "https://a/gone", "https://a/missing", "https://a/err")]
    sent, failed, dead = push.send_all(subs, "raw", "priv", "s")
    assert (sent, failed) == (1, 1)
    assert dead == ["https://a/gone", "https://a/missing"]
