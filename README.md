# pete-common

Shared helpers for Pete's app fleet. See `~/Code/docs/pete-common.md` for the
design notes (written for a .NET mental model).

## Consume it

In an app's `requirements.txt`, pin a tag:

```
pete-common @ git+https://github.com/PeteSounds/pete-common.git@v0.1.0
```

`start.sh` already runs `pip install -r requirements.txt`, so a deploy installs
the pinned version. Apps upgrade independently by bumping the tag.

When developing pete-common itself, override the pin locally (never commit):

```bash
venv/bin/pip install -e ~/Code/pete-common
```

## Release

```bash
git tag v0.2.0 && git push --tags
```

`setuptools-scm` derives the package version from the tag — tags are the single
source of truth and are immutable (never re-tag; bump the version instead).

## Modules

- `pete_common.jsonio` — `load_json` / `write_json` (atomic)
- `pete_common.urls` — `BASE_PATH`-aware `url()` / `url_for()` for Caddy subpaths
- `pete_common.admin` — shared admin auth: `enable_admin(app, password, open_paths=…, open_prefixes=…, mode="gate"|"open")`, `@require_admin`, `csrf_field()`/`@csrf_protect`, fleet SSO via `sso_secret`
- `pete_common.config` — `load_shared(app_root, app_name)`: sibling `fleet.json` (outside every repo → can't be committed) for fleet-wide secrets like `admin_password`/`sso_secret`; `apps.<name>` for per-app shared overrides; `PETE_FLEET_<KEY>` env vars win (e.g. `PETE_FLEET_ADMIN_MODE=off` in CI). `load_config(root, env_prefix=None)`: config.json (else config.example.json) + config.local.json deep overlay + optional `<PREFIX>_<SECTION>_<KEY>` env overrides. `deep_merge(base, override)`.
- `pete_common.push` — `load_vapid(path, private=None, public=None)`, `send(sub, payload, private, subject)` → `SENT`/`DEAD`/`FAILED`, `send_all(...)` → `(sent, failed, dead_endpoints)`. Storage stays in the app; prune the `dead` endpoints. Needs `pywebpush` in the app.
- `pete-vapid [path] [--force]` — console script: generate VAPID keys into `data/vapid.json` (replaces the per-app `scripts/generate-vapid.py`).

## Rules

- Keep it dependency-free; apps bring their own flask/pywebpush/genai.
- Additive changes only — new functions and optional kwargs, never renames or
  removals without bumping a major version.
- Nothing in here may import from an app.
