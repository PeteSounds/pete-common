"""Atomic JSON file read/write helpers."""
import json
import os
from pathlib import Path


def write_json(path, data, indent=2, ensure_ascii=True) -> None:
    """Write JSON atomically: temp file in the same dir, fsync, os.replace.

    A crash mid-write can only truncate the .tmp file, never the real one.
    ensure_ascii=True matches plain json.dump byte output; pass False to write
    raw UTF-8 (e.g. emoji) — both load identically.
    """
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_json(path, default=None):
    """Read a JSON file, returning `default` if it doesn't exist."""
    path = Path(path)
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)
