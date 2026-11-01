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

Env vars `PETE_FLEET_<KEY>` win over both files (e.g. PETE_FLEET_ADMIN_MODE=off
in CI, where there is no fleet.json).

`load_config(root)` is the per-app loader every app used to hand-roll:
config.json (else config.example.json), deep-overlaid by config.local.json,
then optional `<PREFIX>_<SECTION>_<KEY>` env overrides.
"""

import json
import os
from pathlib import Path

FLEET_ENV_PREFIX = "PETE_FLEET_"


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
    for key, value in os.environ.items():
        if key.startswith(FLEET_ENV_PREFIX) and len(key) > len(FLEET_ENV_PREFIX):
            merged[key[len(FLEET_ENV_PREFIX):].lower()] = value
    return merged


def _read_strict(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (in place) and return base."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _coerce(value: str):
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    return value


def load_config(root, env_prefix=None) -> dict:
    """Load an app's config from the directory `root`.

    1. config.json, or config.example.json if there is no config.json
    2. config.local.json deep-merged on top (machine-local, never committed)
    3. if env_prefix is given, env vars `<PREFIX>_<SECTION>_<KEY>` set
       cfg[section][key] (e.g. PETEGRILL_APP_PORT=5059 -> cfg["app"]["port"]);
       "true"/"false" and numbers are coerced.

    Missing files are skipped (returns {} if none exist), but malformed JSON
    raises — a typo in config.json must not silently boot with defaults.
    """
    root = Path(root)
    cfg = {}
    for name in ("config.json", "config.example.json"):
        path = root / name
        if path.exists():
            cfg = _read_strict(path)
            break
    local = root / "config.local.json"
    if local.exists():
        deep_merge(cfg, _read_strict(local))
    if env_prefix:
        prefix = env_prefix.rstrip("_").upper() + "_"
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            section, _, name = key[len(prefix):].lower().partition("_")
            if section and name:
                node = cfg.setdefault(section, {})
                if isinstance(node, dict):
                    node[name] = _coerce(value)
    return cfg
