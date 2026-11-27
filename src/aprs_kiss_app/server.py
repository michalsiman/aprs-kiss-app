"""The station server: APRS & Packet on a Raspberry Pi (or any Linux computer) that runs by itself.

One engine for as long as the computer runs – the TNC, APRS-IS, the iGate, the digipeater, the beacon go on with
no window open. The app's screens are a web page: open http://<the Pi>:8080 on a phone or a computer in the same
network and set everything there (a password asks first, see --set-password). http://<the Pi>:8080/display is a
dashboard for a small screen next to the radio (packaging/raspberry/ starts it in a kiosk browser).

    aprs-kiss-server [--port 8080] [--host 0.0.0.0]
    aprs-kiss-server --set-password        (asks for the web password; empty = none)
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import getpass
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import sys
from pathlib import Path

from aprs_kiss_core.config import VERSION, data_dir, load_config
from aprs_kiss_core.engine import Engine

from . import shared

_LOGGER = logging.getLogger(__name__)

PASSWORD_FILE = "web_password"  # in the data folder: "pbkdf2_sha256$<rounds>$<salt hex>$<hash hex>"
STATE_FILE = "server.json"  # what the server keeps over a restart: transmitting on or off
ROUNDS = 200_000
WRONG_DELAY = 2.0  # seconds after a wrong password


# ─── the web password ────────────────────────────────────────────────────────

def hash_password(password: str, salt: bytes | None = None, rounds: int = ROUNDS) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    mine = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
    return hmac.compare_digest(mine.hex(), digest)


def load_password(folder: Path) -> str:
    with contextlib.suppress(OSError):
        return (folder / PASSWORD_FILE).read_text().strip()
    return ""


def save_password(folder: Path, password: str) -> None:
    path = folder / PASSWORD_FILE
    folder.mkdir(parents=True, exist_ok=True)
    if not password:
        path.unlink(missing_ok=True)
        return
    path.write_text(hash_password(password) + "\n")
    os.chmod(path, 0o600)


def is_local(ip: str | None) -> bool:
    """The display on the Pi itself (a browser on the same computer): no password."""
    if not ip:
        return False
    with contextlib.suppress(ValueError):
        return ipaddress.ip_address(ip.split("%")[0]).is_loopback
    return False


# ─── transmitting, kept over a restart ─────────────────────────────────────────

def load_state(folder: Path) -> dict:
    with contextlib.suppress(OSError, ValueError):
        return json.loads((folder / STATE_FILE).read_text())
    return {}


def save_state(folder: Path, state: dict) -> None:
    with contextlib.suppress(OSError):
        (folder / STATE_FILE).write_text(json.dumps(state))


async def _keep_tx(engine: Engine, folder: Path) -> None:
    """A digipeater or an iGate must transmit again after a power cut: Transmit is remembered."""
    last = engine.tx_enabled
    while True:
        await asyncio.sleep(3)
        if engine.tx_enabled != last:
            last = engine.tx_enabled
            await asyncio.to_thread(save_state, folder, {**load_state(folder), "tx": last})


# ─── the sessions ─────────────────────────────────────────────────────────────

async def page_main(page) -> None:
    """Every browser session: /display gets the dashboard, anything else the app (after the password)."""
    import flet as ft  # noqa: PLC0415

    from . import display  # noqa: PLC0415
    from .app import main as app_main  # noqa: PLC0415
    from .i18n import Translator  # noqa: PLC0415

    if (page.route or "/").startswith("/display"):
        await display.main(page)
        return
    stored = shared.STATE.get("password", "")
    if not stored or is_local(page.client_ip):
        await app_main(page)
        return
    t = Translator(shared.engine().config.language)
    page.title = "APRS & Packet"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    error = ft.Text("", color=ft.Colors.ERROR)
    field = ft.TextField(label=t("srv_password"), password=True, can_reveal_password=True, autofocus=True, width=300)

    async def login(_e=None) -> None:
        if check_password(field.value or "", stored):
            page.controls.clear()
            page.update()
            _LOGGER.info("Web login from %s", page.client_ip)
            await app_main(page)
            return
        _LOGGER.warning("Wrong web password from %s", page.client_ip)
        field.value = ""
        await asyncio.sleep(WRONG_DELAY)
        error.value = t("srv_wrong")
        page.update()
        with contextlib.suppress(Exception):
            await field.focus()

    field.on_submit = login
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(ft.Column([
        ft.Text("APRS & Packet", size=24, weight=ft.FontWeight.BOLD),
        ft.Text(t("srv_title", call=shared.engine().config.callsign or ""), color=ft.Colors.ON_SURFACE_VARIANT),
        field, error,
        ft.FilledButton(t("srv_login"), icon=ft.Icons.LOGIN, on_click=login),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12, tight=True))


async def serve(host: str, port: int) -> None:
    import flet as ft  # noqa: PLC0415

    folder = data_dir()
    config = await asyncio.to_thread(load_config, folder)
    engine = Engine(config, folder)
    await engine.start()
    if load_state(folder).get("tx") and config.configured:
        engine.set_tx(True)
    # the address the display shows for the web (APRS_KISS_WEB_URL: e.g. http://aprs-pi.local:8080); else this
    # computer's address in the network
    shared.STATE.update(engine=engine, folder=folder, port=port, password=load_password(folder),
                        url=os.environ.get("APRS_KISS_WEB_URL", ""))
    _LOGGER.info("APRS & Packet %s station server: http://%s:%d (display: /display), data in %s",
                 VERSION, host, port, folder)
    keeper = asyncio.create_task(_keep_tx(engine, folder))
    os.environ["FLET_FORCE_WEB_SERVER"] = "true"  # no browser opened here; served to the network
    try:
        await ft.run_async(page_main, host=host, port=port, view=ft.AppView.WEB_BROWSER,
                           assets_dir=str(Path(__file__).parent / "web"))
    finally:
        keeper.cancel()
        await engine.stop()


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aprs-kiss-server", description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="0.0.0.0", help="address to listen on (default: every network)")
    parser.add_argument("--port", type=int, default=8080, help="web port (default 8080)")
    parser.add_argument("--set-password", action="store_true", help="set the web password and quit")
    args = parser.parse_args(argv)
    if args.set_password:
        first = getpass.getpass("Web password (empty = none): ")
        if first and getpass.getpass("Again: ") != first:
            sys.exit("The passwords differ – nothing changed.")
        save_password(data_dir(), first)
        print("Password set." if first else "Password removed: anybody in the network can open the app.")
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(serve(args.host, args.port))


if __name__ == "__main__":
    run()
