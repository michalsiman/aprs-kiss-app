"""Is there a newer release on GitHub? Asked at most once a day, standard library only.

Only the public "latest release" of the repository is fetched; nothing about the user is sent.
"""

from __future__ import annotations

import json
import logging
import re
import ssl
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from aprs_kiss_core.config import VERSION

_LOGGER = logging.getLogger(__name__)

LATEST_URL = "https://api.github.com/repos/michalsiman/aprs-kiss-app/releases/latest"
RELEASES_URL = "https://github.com/michalsiman/aprs-kiss-app/releases/latest"
CHECK_EVERY = 24 * 3600
TIMEOUT = 10


def parse_version(text: str) -> tuple[int, ...]:
    """'v0.1.10' → (0, 1, 10); anything after the numbers (-beta) is ignored."""
    m = re.match(r"v?(\d+(?:\.\d+)*)", (text or "").strip())
    return tuple(int(p) for p in m.group(1).split(".")) if m else ()


def is_newer(candidate: str, current: str = VERSION) -> bool:
    a, b = parse_version(candidate), parse_version(current)
    return bool(a) and a > b


@dataclass
class UpdateState:
    last_check: float = 0.0
    latest: str = ""  # newest version seen on GitHub
    url: str = RELEASES_URL
    notified: str = ""  # version the user was already told about
    error: str = ""
    apk_url: str = ""  # the Android package of the latest release, downloaded straight away on a phone

    @property
    def available(self) -> bool:
        return is_newer(self.latest)


def _path(folder: Path) -> Path:
    return folder / "update.json"


def load(folder: Path) -> UpdateState:
    try:
        data = json.loads(_path(folder).read_text(encoding="utf-8"))
        return UpdateState(**{k: v for k, v in data.items() if k in UpdateState.__dataclass_fields__})
    except (OSError, ValueError, TypeError):
        return UpdateState()


def save(folder: Path, state: UpdateState) -> None:
    try:
        _path(folder).write_text(json.dumps(state.__dict__), encoding="utf-8")
    except OSError as err:
        _LOGGER.debug("Could not save the update state: %s", err)


def _tls() -> ssl.SSLContext:
    """Certificate checking that also works on Android and iOS, where Python finds no system CA list."""
    try:
        import certifi  # noqa: PLC0415

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch_latest() -> tuple[str, str, str]:
    """(version, page url, Android package url) of the latest release. Raises OSError/ValueError on failure."""
    req = urllib.request.Request(LATEST_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"aprs-kiss/{VERSION}",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_tls()) as resp:  # noqa: S310 - fixed https URL
        data = json.loads(resp.read().decode("utf-8"))
    apk = next((str(a.get("browser_download_url") or "") for a in data.get("assets") or []
                if str(a.get("name", "")).endswith("-android.apk")), "")
    return str(data.get("tag_name", "")).lstrip("v"), str(data.get("html_url") or RELEASES_URL), apk


def check(folder: Path, force: bool = False, now: float | None = None) -> UpdateState:
    """Ask GitHub if the last check is older than a day (or `force`). Blocking: run it in a thread."""
    state = load(folder)
    now = time.time() if now is None else now
    if not force and state.last_check and now - state.last_check < CHECK_EVERY:
        return state
    try:
        state.latest, state.url, state.apk_url = fetch_latest()
        state.error = ""
    except (OSError, ValueError) as err:
        state.error = str(err) or type(err).__name__
        _LOGGER.debug("Update check failed: %s", state.error)
    state.last_check = now
    save(folder, state)
    return state
