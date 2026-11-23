"""The very first start: which language? The one the device uses is offered, any other can be picked.

Asked once, before the licence warning, so that warning is already in the right language.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import flet as ft

from aprs_kiss_core.config import save_config

from . import i18n
from .i18n import LANGUAGES

if TYPE_CHECKING:
    from .app import App

_LOGGER = logging.getLogger(__name__)


async def detect(page: ft.Page) -> None:
    """Read the device's preferred languages (Android and iOS tell no environment variables)."""
    try:
        info = await page.get_device_info()
        for loc in getattr(info, "locales", None) or []:
            code = i18n.match_language(f"{loc.language_code}_{loc.country_code or ''}".rstrip("_"))
            if code:
                i18n.DEVICE_LANGUAGE = code
                return
    except Exception as err:  # noqa: BLE001 - then the environment decides, as before
        _LOGGER.info("Device language: %s", err)


def needed(app: App) -> bool:
    return not app.engine.config.language_asked


def show(app: App, then) -> None:
    t = app.t
    detected = i18n.system_language()
    choice = ft.Dropdown(
        value="", width=320,
        options=[ft.DropdownOption(key="", text=f"{t('lang_auto')} ({LANGUAGES.get(detected, detected)})"),
                 *[ft.DropdownOption(key=code, text=name) for code, name in LANGUAGES.items()]],
    )

    async def done(_e) -> None:
        conf = app.engine.config
        conf.language, conf.language_asked = choice.value or "", True
        await asyncio.to_thread(save_config, conf, app.folder)
        app.page.pop_dialog()
        if (choice.value or detected) != app.t.language:
            app.build()  # everything in the chosen language
        then()

    app.show_dialog(ft.AlertDialog(
        modal=True,
        icon=ft.Icon(ft.Icons.TRANSLATE, size=36, color=ft.Colors.PRIMARY),
        title=ft.Text(t("lang_title"), text_align=ft.TextAlign.CENTER),
        content=ft.Column([ft.Text(t("lang_detected", name=LANGUAGES.get(detected, detected))), choice,
                           ft.Text(t("lang_later"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)],
                          tight=True, spacing=12, width=360),
        actions=[ft.FilledButton("OK", on_click=done)],
    ))
