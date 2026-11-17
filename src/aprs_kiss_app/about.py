"""The About dialog: what the app is, version, links, author."""

from __future__ import annotations

from importlib import resources
from typing import TYPE_CHECKING

import flet as ft

from aprs_kiss_core.config import VERSION

if TYPE_CHECKING:
    from .app import App

REPO = "https://github.com/michalsiman/aprs-kiss-app"
LINKS = [
    # (text key, icon, url)
    ("about_source", ft.Icons.CODE, REPO),
    ("about_issues", ft.Icons.BUG_REPORT_OUTLINED, f"{REPO}/issues"),
    ("about_releases", ft.Icons.NEW_RELEASES_OUTLINED, f"{REPO}/releases"),
    ("about_firmware", ft.Icons.MEMORY, "https://github.com/armel/uv-k1-k5v3-firmware-custom"),
    ("about_kiss_app", ft.Icons.SETTINGS_INPUT_ANTENNA,
     "https://github.com/armel/uv-k1-k5v3-firmware-custom/wiki/App-KISS-TNC"),
    ("about_ha", ft.Icons.HOME_OUTLINED, "https://github.com/michalsiman/aprs-kiss-ha"),
]
AUTHOR_URL = "https://ok1sim.cz/"


def _icon() -> ft.Control:
    try:
        data = resources.files("aprs_kiss_app").joinpath("icon.png").read_bytes()
        return ft.Image(src=data, width=72, height=72)
    except (FileNotFoundError, OSError):
        return ft.Icon(ft.Icons.CELL_TOWER, size=72)


def _link(text: str, icon, url: str) -> ft.Control:
    return ft.TextButton(text, icon=icon, url=url, tooltip=url,
                         style=ft.ButtonStyle(alignment=ft.Alignment.CENTER_LEFT))


def show_about(app: App) -> None:
    t = app.t
    small = ft.Colors.ON_SURFACE_VARIANT
    content = ft.Column(
        [
            ft.Row(
                [
                    _icon(),
                    ft.Column([
                        ft.Text("APRS & Packet", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(t("about_version", version=VERSION), color=small),
                    ], spacing=2, tight=True),
                ],
                spacing=16,
            ),
            ft.Text(t("about_what")),
            ft.Text(t("about_radio"), color=small, size=13),
            ft.Divider(height=8),
            *[_link(t(key), icon, url) for key, icon, url in LINKS],
            ft.Divider(height=8),
            ft.Text(t("about_author"), weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Text("Michal Šiman, OK1SIM"),
                ft.TextButton("ok1sim.cz", icon=ft.Icons.PUBLIC, url=AUTHOR_URL),
            ], wrap=True, spacing=4),
            ft.Text(t("about_contact"), size=13, color=small),
            ft.Text(t("about_together"), size=13, color=small),
            ft.Divider(height=8),
            ft.Text(t("about_licence"), size=12, color=small),
            ft.Text(f"{t('about_data')}: {app.folder}", size=12, color=small, selectable=True),
        ],
        tight=True,
        spacing=6,
        width=480,
        scroll=ft.ScrollMode.AUTO,
    )
    app.page.show_dialog(ft.AlertDialog(
        content=content,
        actions=[ft.TextButton(t("close"), on_click=lambda _e: app.page.pop_dialog())],
    ))
