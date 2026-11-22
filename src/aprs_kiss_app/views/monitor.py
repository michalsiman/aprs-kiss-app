"""The frame monitor: every frame received and sent, TNC style."""

from __future__ import annotations

import flet as ft

from .base import MONO, View, capped_append

LIMIT = 500


def is_internet(line: str) -> bool:
    """Engine monitor lines look like 'HH:MM:SS << [IS] ...' for APRS-IS traffic."""
    return line[12:17] == "[IS] "


class MonitorView(View):
    key = "monitor"
    icon = ft.Icons.LIST_ALT_OUTLINED
    selected_icon = ft.Icons.LIST_ALT

    def _header(self) -> list[ft.Control]:
        hint = ft.Text(self.t("monitor_hint"), color=ft.Colors.ON_SURFACE_VARIANT, expand=not self.app.compact)
        buttons = [self.internet, self.pause_btn,
                   ft.TextButton(self.t("clear"), icon=ft.Icons.DELETE_SWEEP, on_click=self._clear)]
        if self.app.compact:  # a phone: the hint above, the buttons below
            return [hint, ft.Row(buttons, wrap=True, spacing=0)]
        return [ft.Row([hint, *buttons])]

    def build(self) -> ft.Control:
        self.paused = False
        self.lines = ft.ListView(expand=True, spacing=0, auto_scroll=True, padding=ft.Padding.all(8))
        self.lines.controls = self._all_lines()
        self.internet = ft.Switch(label=self.t("show_internet"), value=self.engine.config.monitor_internet,
                                  on_change=self._internet_changed)
        self.pause_btn = ft.TextButton(self.t("pause"), icon=ft.Icons.PAUSE, on_click=self._toggle)
        return ft.Column(
            [
                *self._header(),
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
        self.pause_btn.text = self.t("resume") if self.paused else self.t("pause")
        self.pause_btn.icon = ft.Icons.PLAY_ARROW if self.paused else ft.Icons.PAUSE
        if not self.paused:
            self.lines.controls = self._all_lines()

    def _wanted(self, line: str) -> bool:
        return self.engine.config.monitor_internet or not is_internet(line)

    def _all_lines(self) -> list[ft.Control]:
        source = self.engine.monitor if self.engine.config.monitor_internet else self.engine.monitor_rf
        return [self._line(line) for line in source][-LIMIT:]

    def _internet_changed(self, e) -> None:
        """Saved like the map's choice; the lines already received are filtered again at once."""
        self.engine.config.monitor_internet = bool(e.control.value)
        self.app.save_config_soon()
        if not self.paused:
            self.lines.controls = self._all_lines()
        self.app.page.update()

    def _clear(self, _e) -> None:
        self.engine.monitor.clear()
        self.engine.monitor_rf.clear()
        self.lines.controls.clear()
