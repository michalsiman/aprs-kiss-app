"""`aprs-kiss` command (pip/pipx install)."""

import flet as ft

from .app import main


def run() -> None:
    ft.run(main)
