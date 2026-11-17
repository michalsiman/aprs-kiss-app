"""The legend for the map and the station list, and the shared "stations from the internet" choice."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import flet as ft

from .symbols import UNKNOWN, symbol_info

if TYPE_CHECKING:
    from .app import App

# Label colours on the map and in the list.
COLOR_RF = ft.Colors.BLUE
COLOR_IS = ft.Colors.BLUE_GREY
COLOR_TRACKED = ft.Colors.ORANGE
COLOR_ME = ft.Colors.RED


def station_color(app: App, entry: dict) -> str:
    if entry["call"].upper() in app.tracked():
        return COLOR_TRACKED
    return COLOR_RF if entry.get("last_rf") else COLOR_IS


def visible(app: App, entry: dict) -> bool:
    """Stations seen only on APRS-IS are shown when the user wants them."""
    return bool(entry.get("last_rf")) or app.engine.config.show_internet


def internet_checkbox(app: App) -> ft.Checkbox:
    """The same choice on the map and in the list; changing it saves it and updates both."""
    return ft.Checkbox(label=app.t("show_internet"), value=app.engine.config.show_internet,
                       on_change=lambda e: app.set_show_internet(bool(e.control.value)))


def _row(left: ft.Control, text: str) -> ft.Control:
    return ft.Row([ft.Container(left, width=64, alignment=ft.Alignment.CENTER), ft.Text(text, expand=True)],
                  spacing=8)


def _swatch(color, bold=False) -> ft.Control:
    return ft.Container(ft.Text("OK1ABC", size=10, no_wrap=True, color=color,
                                weight=ft.FontWeight.BOLD if bold else None),
                        bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.SURFACE), border_radius=4,
                        padding=ft.Padding.symmetric(horizontal=3))


def show_legend(app: App) -> None:
    t = app.t
    lang = t.language
    entries = [e for e in app.engine.station.heard.values() if visible(app, e)]
    counts: Counter[tuple[str, str]] = Counter()
    unknown: Counter[str] = Counter()
    for e in entries:
        pic, name, known = symbol_info(e.get("symbol_table"), e.get("symbol"), lang)
        if known:
            counts[(pic, name)] += 1
        else:
            unknown[name or "?"] += 1

    rows: list[ft.Control] = [
        ft.Text(t("legend_colours"), weight=ft.FontWeight.BOLD),
        _row(_swatch(COLOR_RF, True), t("legend_rf")),
        _row(_swatch(COLOR_IS), t("legend_is")),
        _row(_swatch(COLOR_TRACKED, True), t("legend_tracked")),
        _row(_swatch(COLOR_ME, True), t("legend_me")),
        ft.Divider(height=8),
        ft.Text(t("legend_symbols"), weight=ft.FontWeight.BOLD),
        ft.Text(t("legend_symbols_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
    ]
    for (pic, name), n in sorted(counts.items(), key=lambda kv: -kv[1]):
        rows.append(_row(ft.Text(pic, size=20), f"{name} ({n})"))
    if unknown:
        codes = ", ".join(f"{code} ({n})" for code, n in unknown.most_common())
        rows.append(_row(ft.Text(UNKNOWN, size=20), f"{t('legend_unknown')}: {codes}"))
    if not counts and not unknown:
        rows.append(ft.Text(t("no_stations"), color=ft.Colors.ON_SURFACE_VARIANT))

    app.page.show_dialog(ft.AlertDialog(
        title=ft.Text(t("legend")),
        content=ft.Column(rows, tight=True, spacing=6, width=440, scroll=ft.ScrollMode.AUTO),
        actions=[ft.TextButton(t("close"), on_click=lambda _e: app.page.pop_dialog())],
    ))
