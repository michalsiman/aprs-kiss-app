"""The station server (server.py): one engine for every browser session, set before the web server starts.
Empty in the normal app, where each window has its own engine."""

from __future__ import annotations

from typing import Any

STATE: dict[str, Any] = {}


def engine():
    """The shared engine, or None (the normal app)."""
    return STATE.get("engine")
