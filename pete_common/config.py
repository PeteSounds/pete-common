"""Shared fleet config — one file for values every app needs.

A sibling `fleet.json` next to the app directories (~/Code/fleet.json locally,
/root/fleet.json on the VM). Living OUTSIDE every repo means it can never be
committed — safer than in-repo config.local.json.

    {
      "admin_password": "...",
      "sso_secret": "64-hex",
      "apps": {
        "petepills":   {"base_path": "/pills"},
        "lincmadlibs": {"base_path": "/madlibs"}
      }
    }

Top-level keys apply to every app; `apps.<name>` overrides per app. An app's
own config.json/config.local.json still wins — this is the fallback layer.

`fleet.local.json` (same dir) is merged on top and is machine-local by
convention — it is never copied to the VM. Good for dev-box overrides like
{"admin_mode": "off"}.
"""

import json
from pathlib import Path


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def load_shared(app_root, app_name=None) -> dict:
    """Load fleet.json + fleet.local.json sitting next to app_root.

    fleet.local.json is machine-local (never shipped): use it for things like
    "admin_mode": "off" on a dev box. Local keys win over fleet.json; then
    apps.<name> overrides both. Missing files → {}.
    """
    merged = {}
    for name in ("fleet.json", "fleet.local.json"):
        data = _read(Path(app_root).parent / name)
        apps = data.pop("apps", {})
        merged.update({k: v for k, v in data.items()})
        merged.setdefault("_apps", {}).update(apps)
    app_overrides = merged.pop("_apps", {})
    merged.update(app_overrides.get(app_name, {}))
    return merged
