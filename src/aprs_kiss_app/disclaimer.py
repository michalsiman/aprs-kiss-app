"""The warning shown once, at the very first start: this app makes a radio transmit.

It has to be accepted before the app can be used; the other checks inside the app (the Transmit
switch, the licence sentence for APRS-IS, the typed confirmations for BBS SERVER and TAK) stay.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import flet as ft

from aprs_kiss_core.config import save_config

if TYPE_CHECKING:
    from .app import App

POINTS = ("disc_licence", "disc_harm", "disc_rx", "disc_resp")


def needed(app: App) -> bool:
    return not app.engine.config.disclaimer_accepted


def show(app: App) -> None:
    t = app.t
    body = ft.Column(
        [ft.Text(t("disc_intro"))]
        + [ft.Row([ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.ERROR, size=20),
                   ft.Text(t(key), expand=True)], vertical_alignment=ft.CrossAxisAlignment.START)
           for key in POINTS],
        tight=True, spacing=12, scroll=ft.ScrollMode.AUTO,
    )
    dialog = ft.AlertDialog(
        modal=True,  # no way around it: tapping outside or Back does not close it
        icon=ft.Icon(ft.Icons.CELL_TOWER, color=ft.Colors.ERROR, size=40),
        title=ft.Text(t("disc_title"), text_align=ft.TextAlign.CENTER),
        content=ft.Container(body, width=560),
        actions=[
            ft.TextButton(t("disc_decline"), on_click=lambda _e: app.page.run_task(_decline, app, dialog)),
            ft.FilledButton(t("disc_accept"), icon=ft.Icons.CHECK,
                            on_click=lambda _e: app.page.run_task(_accept, app, dialog)),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    app.show_dialog(dialog)


async def _accept(app: App, dialog: ft.AlertDialog) -> None:
    app.engine.config.disclaimer_accepted = True
    await asyncio.to_thread(save_config, app.engine.config, app.folder)
    app.page.pop_dialog()
    app.page.update()


async def _decline(app: App, dialog: ft.AlertDialog) -> None:
    """A computer: the app closes. A phone cannot close an app itself: it says so and asks again."""
    if not app.mobile:
        try:
            await app.page.window.close()
            return
        except Exception:  # noqa: BLE001 - e.g. in a browser: ask again below
            pass
    t = app.t
    app.page.pop_dialog()
    again = ft.AlertDialog(
        modal=True,
        title=ft.Text(t("disc_title")),
        content=ft.Text(t("disc_declined")),
        actions=[ft.FilledButton(t("disc_again"), on_click=lambda _e: (app.page.pop_dialog(), show(app)))],
    )
    app.show_dialog(again)
