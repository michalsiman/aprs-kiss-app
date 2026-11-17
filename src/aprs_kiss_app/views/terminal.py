"""Packet radio terminal: AX.25 connected mode to a BBS or node."""

from __future__ import annotations

import flet as ft

from aprs_kiss_core.engine import TransmitRefused

from .base import MONO, View, capped_append

LIMIT = 2000


class TerminalView(View):
    key = "terminal"
    icon = ft.Icons.TERMINAL_OUTLINED
    selected_icon = ft.Icons.TERMINAL

    def build(self) -> ft.Control:
        self.remote = ft.TextField(label=self.t("remote"), hint_text="OK0BBS", width=200, dense=True,
                                   capitalization=ft.TextCapitalization.CHARACTERS, on_submit=self._connect)
        self.path = ft.TextField(label=self.t("path"), width=200, dense=True,
                                 capitalization=ft.TextCapitalization.CHARACTERS)
        self.connect_btn = ft.FilledButton(self.t("connect"), icon=ft.Icons.LINK, on_click=self._connect)
        self.disconnect_btn = ft.OutlinedButton(self.t("disconnect"), icon=ft.Icons.LINK_OFF, on_click=self._disconnect)
        self.state = ft.Text(self.t("not_connected_session"), color=ft.Colors.ON_SURFACE_VARIANT)
        self.lines = ft.ListView(expand=True, spacing=0, auto_scroll=True, padding=ft.Padding.all(8))
        self._open: ft.Text | None = None  # the received line still waiting for its end
        self.input = ft.TextField(hint_text=self.t("type_here"), expand=True, dense=True, on_submit=self._send,
                                  text_style=ft.TextStyle(font_family=MONO))
        return ft.Column(
            [
                ft.Row([self.remote, self.path, self.connect_btn, self.disconnect_btn], wrap=True),
                self.state,
                ft.Container(ft.SelectionArea(self.lines), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
                ft.Row([self.input, ft.IconButton(ft.Icons.SEND, tooltip=self.t("send"), on_click=self._send)]),
            ],
            expand=True,
        )

    @property
    def current(self) -> str:
        return (self.remote.value or "").strip().upper()

    def _add(self, e: dict) -> None:
        """Received text is a stream: a chunk (one I frame) continues the line the previous one left open."""
        text = e["text"].replace("\r\n", "\n").replace("\r", "\n")
        if e["kind"] == "rx":
            parts = text.split("\n")
            if self._open is not None:
                self._open.value += parts.pop(0)
            for part in parts:
                self._open = ft.Text(part, font_family=MONO, size=13)
                capped_append(self.lines, self._open, LIMIT)
            return
        self._open = None
        if e["kind"] == "state":
            line = ft.Text(f"*** {e['remote']}: {text.rstrip()}", font_family=MONO, size=13, italic=True,
                           color=ft.Colors.ON_SURFACE_VARIANT)
        else:
            line = ft.Text(text.rstrip("\n"), font_family=MONO, size=13, color=ft.Colors.ORANGE)
        capped_append(self.lines, line, LIMIT)

    def on_event(self, kind, data) -> None:
        if kind == "terminal" and data["entry"]["remote"] == self.current:
            self._add(data["entry"])

    def refresh(self) -> None:
        states = self.engine.session_states()
        state = states.get(self.current)
        if not self.current and len(states) == 1:
            self.remote.value = next(iter(states))
            state = states[self.remote.value]
        self.state.value = f"{self.current}: {state}" if state else self.t("not_connected_session")
        self.state.color = ft.Colors.GREEN if state == "connected" else ft.Colors.ON_SURFACE_VARIANT
        self.disconnect_btn.disabled = not state
        self.input.disabled = state != "connected"

    def _reload_lines(self) -> None:
        self.lines.controls = []
        self._open = None
        for e in self.engine.terminal:
            if e["remote"] == self.current:
                self._add(e)

    async def _connect(self, _e) -> None:
        try:
            self.engine.connect(self.current, self.path.value or "")
        except TransmitRefused:
            self.app.toast(self.t("tx_refused"), error=True)
            return
        except (ConnectionError, ValueError) as err:
            self.app.toast(f"{self.t('not_sent')}: {err}", error=True)
            return
        self.remote.value = self.current
        self._reload_lines()
        self.refresh()

    def _disconnect(self, _e) -> None:
        try:
            self.engine.disconnect(self.current)
        except ValueError as err:
            self.app.toast(str(err), error=True)

    async def _send(self, _e) -> None:
        text = self.input.value or ""
        try:
            self.engine.send_text(self.current, text + "\n")
        except (ConnectionError, ValueError) as err:
            self.app.toast(f"{self.t('not_sent')}: {err}", error=True)
            return
        self.input.value = ""
        await self.input.focus()
