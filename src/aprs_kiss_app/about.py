"""The About dialog: what the app is, version, links, author."""

from __future__ import annotations

from importlib import resources
from typing import TYPE_CHECKING

import flet as ft

from aprs_kiss_core.config import VERSION

from .views.base import clock

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


def _update_text(app: App) -> tuple[str, str | None]:
    """(text, colour) describing the last check for a new version."""
    t = app.t
    st = app.update_state
    if st.available:
        return t("update_available", version=st.latest), ft.Colors.PRIMARY
    if not st.last_check:
        return t("update_never"), ft.Colors.ON_SURFACE_VARIANT
    when = t("update_checked", when=clock(st.last_check))
    if st.error:
        return f"{t('update_failed')} ({when}).", ft.Colors.ON_SURFACE_VARIANT
    return f"{t('update_none')} ({when})", ft.Colors.ON_SURFACE_VARIANT


def show_about(app: App) -> None:
    t = app.t
    small = ft.Colors.ON_SURFACE_VARIANT
    text, color = _update_text(app)
    update_text = ft.Text(text, size=13, color=color)
    update_link = ft.TextButton(t("update_download" if app.android else "update_show"), icon=ft.Icons.NEW_RELEASES,
                                visible=app.update_state.available,
                                on_click=lambda _e: app.page.run_task(app._open_release))

    async def check_now(e) -> None:
        e.control.disabled = True
        update_text.value = "…"
        app.page.update()
        await app.check_updates(force=True)
        update_text.value, update_text.color = _update_text(app)
        update_link.visible = app.update_state.available
        e.control.disabled = False
        app.page.update()
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
            ft.Row([update_text, update_link,
                    ft.TextButton(t("update_check_now"), icon=ft.Icons.REFRESH, on_click=check_now)],
                   wrap=True, spacing=4),
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
    app.show_dialog(ft.AlertDialog(
        content=content,
        actions=[ft.TextButton(t("close"), on_click=lambda _e: app.page.pop_dialog())],
    ))
