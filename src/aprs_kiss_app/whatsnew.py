"""After an update to a new stable version: once, what changed since the version run before (from CHANGELOG.md
in the package). Betas show nothing and leave the mark, so the next stable version lists their changes too."""

from __future__ import annotations

import logging
from importlib import resources
from typing import TYPE_CHECKING

import flet as ft

from aprs_kiss_core import changelog
from aprs_kiss_core.config import BETA, VERSION

if TYPE_CHECKING:
    from .app import App

_LOGGER = logging.getLogger(__name__)


def _text() -> str:
    try:
        return resources.files("aprs_kiss_app").joinpath("CHANGELOG.md").read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def check(app: App, first_start: bool) -> None:
    """Called at start, after the first-start dialogs (a first start only remembers the version)."""
    conf = app.engine.config
    if BETA or conf.seen_version == VERSION:
        return
    seen = conf.seen_version
    conf.seen_version = VERSION  # once: saved now, closed or not
    app.save_config_soon()
    if first_start:
        return
    try:
        text = changelog.since(_text(), seen, VERSION)
    except Exception:  # noqa: BLE001 - a broken file must not stop the app
        _LOGGER.exception("changelog")
        return
    if text:
        show(app, text)


def show(app: App, text: str) -> None:
    t = app.t
    dialog = ft.AlertDialog(
        icon=ft.Icon(ft.Icons.NEW_RELEASES_OUTLINED, color=ft.Colors.PRIMARY, size=36),
        title=ft.Text(t("whatsnew_title", version=VERSION), text_align=ft.TextAlign.CENTER),
        content=ft.Container(
            ft.Column([ft.Markdown(text, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)],
                      scroll=ft.ScrollMode.AUTO, tight=True),
            width=600, height=min(520, max(240, (app.page.height or 700) - 220))),
        actions=[ft.FilledButton(t("whatsnew_close"), on_click=lambda _e: app.page.pop_dialog())],
    )
    app.show_dialog(dialog)
