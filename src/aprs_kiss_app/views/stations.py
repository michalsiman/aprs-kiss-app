"""Stations heard on the radio or seen on APRS-IS, newest first."""

from __future__ import annotations

import time

import flet as ft

from ..legend import internet_checkbox, show_legend, station_color, visible
from ..symbols import symbol_info
from .base import View, bearing, distance_km


def describe(app, entry: dict) -> str:
    """One line about a heard station: distance, how it was heard, symbol, comment."""
    conf = app.engine.config
    parts = []
    if conf.has_position and entry.get("latitude") is not None:
        d = distance_km(conf.latitude, conf.longitude, entry["latitude"], entry["longitude"])
        parts.append(f"{d:.0f} km {bearing(conf.latitude, conf.longitude, entry['latitude'], entry['longitude'])}")
    parts.append(app.t("via_heard_rf") if entry.get("last_rf") else app.t("via_heard_is"))
    if entry.get("gated_by"):
        parts.append(f"iGate {entry['gated_by']}")
    _, name, known = symbol_info(entry.get("symbol_table"), entry.get("symbol"), app.t.language)
    if known:
        parts.append(name)
    text = entry.get("comment") or entry.get("status") or ""
    if text:
        parts.append(str(text))
    return " · ".join(parts)


class StationsView(View):
    key = "stations"
    icon = ft.Icons.CELL_TOWER_OUTLINED
    selected_icon = ft.Icons.CELL_TOWER

    def build(self) -> ft.Control:
        self._signature = None
        self.filter = ft.TextField(hint_text=self.t("filter"), prefix_icon=ft.Icons.SEARCH, dense=True, width=240,
                                   on_change=lambda _e: self.force())
        self.internet = internet_checkbox(self.app)
        self.count = ft.Text(color=ft.Colors.ON_SURFACE_VARIANT)
        self.list = ft.ListView(expand=True, spacing=0)
        return ft.Column(
            [
                ft.Row([self.filter, self.internet, self.count,
                        ft.TextButton(self.t("legend"), icon=ft.Icons.HELP_OUTLINE,
                                      on_click=lambda _e: show_legend(self.app))],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.list,
            ],
            expand=True,
        )

    def force(self) -> None:
        self._signature = None
        self.internet.value = self.engine.config.show_internet
        self.refresh()

    def refresh(self) -> None:
        heard = self.engine.station.heard
        now = time.time()
        # Ages are shown rounded, so a refresh every 30 s is enough when nothing new was heard.
        signature = (len(heard), next(reversed(heard), None), heard[next(reversed(heard))]["count"] if heard else 0,
                     int(now // 30))
        if signature == self._signature:
            return
        self._signature = signature
        needle = (self.filter.value or "").strip().upper()
        entries = [e for e in reversed(heard.values())
                   if (not needle or needle in e["call"].upper()) and visible(self.app, e)]
        self.count.value = f"{len(entries)} / {len(heard)}"
        if not entries:
            self.list.controls = [ft.Text(self.t("no_stations"), color=ft.Colors.ON_SURFACE_VARIANT)]
            return
        lang = self.t.language
        self.list.controls = []
        for e in entries[:300]:
            pic, name, _known = symbol_info(e.get("symbol_table"), e.get("symbol"), lang)
            self.list.controls.append(ft.ListTile(
                leading=ft.Text(pic, size=24, tooltip=name or None),
                title=ft.Text(e["call"], weight=ft.FontWeight.BOLD, color=station_color(self.app, e)),
                subtitle=ft.Text(describe(self.app, e), max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                trailing=ft.Text(self.t.age(now - e["last_heard"]), size=12),
                dense=True,
                on_click=lambda _e, c=e["call"]: self.app.show_station(c),
            ))
