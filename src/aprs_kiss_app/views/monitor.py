"""The frame monitor: every frame received and sent, TNC style."""

from __future__ import annotations

import flet as ft

from .base import MONO, View, capped_append

LIMIT = 500


class MonitorView(View):
    key = "monitor"
    icon = ft.Icons.LIST_ALT_OUTLINED
    selected_icon = ft.Icons.LIST_ALT

    def build(self) -> ft.Control:
        self.paused = False
        self.lines = ft.ListView(expand=True, spacing=0, auto_scroll=True, padding=ft.Padding.all(8))
        for line in self.engine.monitor:
            self.lines.controls.append(self._line(line))
        self.pause_btn = ft.TextButton(self.t("pause"), icon=ft.Icons.PAUSE, on_click=self._toggle)
        return ft.Column(
            [
                ft.Row([ft.Text(self.t("monitor_hint"), color=ft.Colors.ON_SURFACE_VARIANT, expand=True),
                        self.pause_btn,
                        ft.TextButton(self.t("clear"), icon=ft.Icons.DELETE_SWEEP, on_click=self._clear)]),
                ft.Container(ft.SelectionArea(self.lines), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
            ],
            expand=True,
        )

    def _line(self, line: str) -> ft.Text:
        outgoing = " >> " in line[:12]
        internet = "[IS]" in line[:20]
        color = ft.Colors.ORANGE if outgoing else (ft.Colors.BLUE_GREY if internet else None)
        return ft.Text(line, font_family=MONO, size=12, color=color, no_wrap=False)

    def on_event(self, kind, data) -> None:
        if kind == "monitor" and not self.paused:
            capped_append(self.lines, self._line(data["line"]), LIMIT)

    def _toggle(self, _e) -> None:
        self.paused = not self.paused
        self.pause_btn.text = self.t("resume") if self.paused else self.t("pause")
        self.pause_btn.icon = ft.Icons.PLAY_ARROW if self.paused else ft.Icons.PAUSE
        if not self.paused:
            self.lines.controls = [self._line(line) for line in self.engine.monitor]

    def _clear(self, _e) -> None:
        self.engine.monitor.clear()
        self.lines.controls.clear()
