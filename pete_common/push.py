"""Web Push helpers: VAPID key loading, sending, dead-subscription detection.

pywebpush is imported lazily, so apps without push can still import
pete_common. Apps that push must list `pywebpush` in requirements.txt.

    from pete_common import push

    private, public = push.load_vapid(DATA_DIR / "vapid.json")
    result = push.send(sub, {"title": "Pills", "body": "8:00"}, private,
                       subject="mailto:push@petepills.local")
    if result == push.DEAD:
        ...prune sub from storage...

    # or a whole batch:
    sent, failed, dead = push.send_all(subs, payload, private, subject=...)
    ...remove `dead` endpoints from storage...

Storage stays in the app (JSON file, SQLite, ...) — this module only sends.
Generate keys with the `pete-vapid` command (installed with pete-common).
"""

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger(__name__)

SENT = "sent"
DEAD = "dead"      # 404/410: subscription is gone — caller should delete it
FAILED = "failed"  # anything else: keep the subscription, maybe retry later


def load_vapid(path, private=None, public=None):
    """Return (private_b64url, public_b64url), or (None, None) if unavailable.

    Explicit keys (e.g. from env vars) win over the file. The file uses the
    fleet format written by `pete-vapid` (private_base64url/public_base64url);
    the older private_key/public_key names are accepted too.
    """
    if private and public:
        return private, public
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None, None
    priv = data.get("private_base64url") or data.get("private_key")
    pub = data.get("public_base64url") or data.get("public_key")
    if priv and pub:
        return priv, pub
    return None, None


def _audience(endpoint: str) -> str:
    parsed = urlparse(endpoint or "")
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""


def _status(exc):
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None)


def send(subscription: dict, payload, private_key: str, subject: str,
         ttl: int = 3600, timeout: float = 15) -> str:
    """Send one push. Returns SENT, DEAD (prune it) or FAILED.

    payload may be a dict (JSON-encoded here) or a pre-encoded str.
    subject is the VAPID contact, e.g. "mailto:push@petegrill.local".
    """
    if not private_key:
        log.warning("push: no VAPID private key, not sending")
        return FAILED
    from pywebpush import webpush

    endpoint = subscription.get("endpoint", "")
    claims = {"sub": subject}
    aud = _audience(endpoint)
    if aud:
        claims["aud"] = aud
    data = payload if isinstance(payload, str) else json.dumps(payload)
    try:
        webpush(
            subscription_info=subscription,
            data=data,
            vapid_private_key=private_key,
            vapid_claims=claims,
            ttl=ttl,
            timeout=timeout,
        )
        return SENT
    except Exception as exc:  # WebPushException, network errors, bad keys...
        status = _status(exc)
        log.warning("push failed (%s) for %s: %s", status, endpoint[:60], exc)
        return DEAD if status in (404, 410) else FAILED


def send_all(subscriptions, payload, private_key: str, subject: str, **kwargs):
    """Send to many. Returns (sent_count, failed_count, dead_endpoints)."""
    sent = failed = 0
    dead = []
    for sub in subscriptions:
        result = send(sub, payload, private_key, subject, **kwargs)
        if result == SENT:
            sent += 1
        elif result == DEAD:
            dead.append(sub.get("endpoint"))
        else:
            failed += 1
    return sent, failed, dead
