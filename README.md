# pete-common

Shared helpers for Pete's app fleet. See `~/Code/docs/pete-common.md` for the
design notes (written for a .NET mental model).

## Consume it

In an app's `requirements.txt`, pin a tag:

```
pete-common @ git+ssh://git@github.com/PeteSounds/pete-common.git@v0.1.0
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

## Rules

- Keep it dependency-free; apps bring their own flask/pywebpush/genai.
- Additive changes only — new functions and optional kwargs, never renames or
  removals without bumping a major version.
- Nothing in here may import from an app.
