"""The frame monitor: every frame received and sent, TNC style."""

from __future__ import annotations

import flet as ft

from .base import MONO, View, capped_append, toggle

LIMIT = 500


def is_internet(line: str) -> bool:
    """Engine monitor lines look like 'HH:MM:SS << [IS] ...' for APRS-IS traffic."""
    return line[12:17] == "[IS] "


class MonitorView(View):
    key = "monitor"
    icon = ft.Icons.LIST_ALT_OUTLINED
    selected_icon = ft.Icons.LIST_ALT

    def build(self) -> ft.Control:
        self.paused = False
        self.lines = ft.ListView(expand=True, spacing=0, auto_scroll=True, padding=ft.Padding.all(8))
        self.lines.controls = self._all_lines()
        # The same lit / crossed-out icons as on the map: little room taken, the state seen at a glance.
        self.internet = toggle(ft.Icons.PUBLIC_OFF, ft.Icons.PUBLIC, self.engine.config.monitor_internet,
                               self.t("show_internet"), self._internet_changed)
        self.pause_btn = toggle(ft.Icons.PAUSE, ft.Icons.PLAY_ARROW, False, self.t("pause"), self._toggle)
        clear = ft.IconButton(ft.Icons.DELETE_SWEEP_OUTLINED, tooltip=self.t("clear"), on_click=self._clear)
        hint = ft.Text(self.t("monitor_hint"), color=ft.Colors.ON_SURFACE_VARIANT, expand=True,
                       size=12 if self.app.compact else None)
        return ft.Column(
            [
                ft.Row([hint, self.internet, self.pause_btn, clear], spacing=0),
                ft.Container(ft.SelectionArea(self.lines), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
            ],
            expand=True,
        )

    def _line(self, line: str) -> ft.Text:
        outgoing = " >> " in line[:12]
        internet = is_internet(line)
        color = ft.Colors.ORANGE if outgoing else (ft.Colors.BLUE_GREY if internet else None)
        return ft.Text(line, font_family=MONO, size=12, color=color, no_wrap=False)

    def on_event(self, kind, data) -> None:
        if kind == "monitor" and not self.paused and self._wanted(data["line"]):
            capped_append(self.lines, self._line(data["line"]), LIMIT)

    def _toggle(self, _e) -> None:
        self.paused = not self.paused
        self.pause_btn.selected = self.paused  # lit while paused; a tap goes on
        self.pause_btn.tooltip = self.t("resume") if self.paused else self.t("pause")
        if not self.paused:
            self.lines.controls = self._all_lines()

    def _wanted(self, line: str) -> bool:
        return self.engine.config.monitor_internet or not is_internet(line)

    def _all_lines(self) -> list[ft.Control]:
        source = self.engine.monitor if self.engine.config.monitor_internet else self.engine.monitor_rf
        return [self._line(line) for line in source][-LIMIT:]

    def _internet_changed(self, e) -> None:
        """Saved like the map's choice; the lines already received are filtered again at once."""
        self.engine.config.monitor_internet = not self.engine.config.monitor_internet
        self.internet.selected = self.engine.config.monitor_internet
        self.app.save_config_soon()
        if not self.paused:
            self.lines.controls = self._all_lines()
        self.app.page.update()

    def _clear(self, _e) -> None:
        self.engine.monitor.clear()
        self.engine.monitor_rf.clear()
        self.lines.controls.clear()
