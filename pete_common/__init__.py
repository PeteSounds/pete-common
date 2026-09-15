"""Shared helpers for Pete's app fleet. Keep this dependency-free."""
from importlib.metadata import version as _v

try:
    __version__ = _v("pete-common")
except Exception:
    __version__ = "0+unknown"
