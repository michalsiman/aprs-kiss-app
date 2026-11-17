"""Stations heard on the radio or seen on APRS-IS, newest first."""

from __future__ import annotations

import time

import flet as ft

from ..symbols import emoji
from .base import View, bearing, distance_km


def describe(app, entry: dict) -> str:
    """One line about a heard station: distance, path, comment."""
    conf = app.engine.config
    parts = []
    if conf.has_position and entry.get("latitude") is not None:
        d = distance_km(conf.latitude, conf.longitude, entry["latitude"], entry["longitude"])
        parts.append(f"{d:.0f} km {bearing(conf.latitude, conf.longitude, entry['latitude'], entry['longitude'])}")
    via = "RF" if entry.get("last_rf") else "IS"
    parts.append(via)
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
        self.filter = ft.TextField(hint_text=self.t("filter"), prefix_icon=ft.Icons.SEARCH, dense=True, width=260,
                                   on_change=lambda _e: self._force())
        self.rf_only = ft.Checkbox(label=self.t("only_rf"), value=False, on_change=lambda _e: self._force())
        self.count = ft.Text(color=ft.Colors.ON_SURFACE_VARIANT)
        self.list = ft.ListView(expand=True, spacing=0)
        return ft.Column([ft.Row([self.filter, self.rf_only, self.count]), self.list], expand=True)

    def _force(self) -> None:
        self._signature = None
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
                   if (not needle or needle in e["call"].upper()) and (not self.rf_only.value or e.get("last_rf"))]
        self.count.value = f"{len(entries)} / {len(heard)}"
        if not entries:
            self.list.controls = [ft.Text(self.t("no_stations"), color=ft.Colors.ON_SURFACE_VARIANT)]
            return
        tracked = self.app.tracked()
        self.list.controls = [
            ft.ListTile(
                leading=ft.Text(emoji(e.get("symbol_table"), e.get("symbol")), size=24),
                title=ft.Text(e["call"], weight=ft.FontWeight.BOLD,
                              color=ft.Colors.ORANGE if e["call"].upper() in tracked else None),
                subtitle=ft.Text(describe(self.app, e), max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                trailing=ft.Text(self.t.age(now - e["last_heard"]), size=12),
                dense=True,
                on_click=lambda _e, c=e["call"]: self.app.show_station(c),
            )
            for e in entries[:300]
        ]
