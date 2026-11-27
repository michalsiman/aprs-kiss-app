"""Packet radio terminal: AX.25 connected mode to a BBS or node."""

from __future__ import annotations

import time

import flet as ft

from aprs_kiss_core.engine import TransmitRefused

from .base import MONO, View, capped_append

LIMIT = 2000
NEW = "\x00new"  # the "New station…" item of the saved list


class TerminalView(View):
    key = "terminal"
    icon = ft.Icons.TERMINAL_OUTLINED
    selected_icon = ft.Icons.TERMINAL

    def build(self) -> ft.Control:
        self.remote = ft.TextField(label=self.t("remote"), hint_text="OK0BBS", width=160, dense=True,
                                   capitalization=ft.TextCapitalization.CHARACTERS, on_submit=self._connect)
        self.path = ft.TextField(label=self.t("path"), width=160, dense=True,
                                 capitalization=ft.TextCapitalization.CHARACTERS)
        # Mostly a saved station is picked; a new one opens the fields for its callsign and path.
        self.saved = ft.Dropdown(label=self.t("bbs_saved"), dense=True, on_select=self._pick,
                                 expand=self.app.compact, width=None if self.app.compact else 340)
        self.save_btn = ft.IconButton(ft.Icons.BOOKMARK_ADD_OUTLINED, tooltip=self.t("bbs_save"), on_click=self._save)
        self.remove_btn = ft.IconButton(ft.Icons.BOOKMARK_REMOVE_OUTLINED, tooltip=self.t("bbs_remove"),
                                        on_click=self._remove)
        # Over AX.25 packet (the TNC) or VARA FM; the choice appears once VARA is set up in Settings.
        self.via = ft.Dropdown(label=self.t("connection"), width=210, dense=True, value="ax25",
                               visible=self.engine.vara is not None,
                               options=[ft.DropdownOption(key="ax25", text=self.t("via_packet")),
                                        ft.DropdownOption(key="vara", text="VARA FM")])
        self.connect_btn = ft.IconButton(ft.Icons.LINK, tooltip=self.t("connect"), on_click=self._connect,
                                         style=ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.PRIMARY)))
        self.disconnect_btn = ft.IconButton(ft.Icons.LINK_OFF, tooltip=self.t("disconnect"), on_click=self._disconnect)
        self.new_row = ft.Row([self.remote, self.path, self.save_btn], wrap=True, run_spacing=4)
        self._fill_saved()
        self.state = ft.Text(self.t("not_connected_session"), color=ft.Colors.ON_SURFACE_VARIANT)
        self.lines = ft.ListView(expand=True, spacing=0, auto_scroll=True, auto_scroll_animation=0, padding=ft.Padding.all(8))
        self._open: ft.Text | None = None  # the received line still waiting for its end
        self.input = ft.TextField(hint_text=self.t("type_here"), expand=True, dense=True, on_submit=self._send,
                                  text_style=ft.TextStyle(font_family=MONO))
        return ft.Column(
            [
                ft.Row([self.saved, self.remove_btn, self.connect_btn, self.disconnect_btn], spacing=2),
                self.new_row,
                self.via,
                self.state,
                ft.Container(ft.SelectionArea(self.lines), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
                ft.Row([self.input, ft.IconButton(ft.Icons.SEND, tooltip=self.t("send"), on_click=self._send)]),
            ],
            expand=True,
        )

    # ─── saved BBSes ──────────────────────────────────────────────────────

    def _fill_saved(self) -> None:
        items = self.engine.config.saved_bbs()
        self.saved.options = [ft.DropdownOption(key=i["call"], text=f"{i['call']} via {i['path']}" if i["path"]
                                                else i["call"]) for i in items]
        self.saved.options.append(ft.DropdownOption(key=NEW, text=self.t("term_new"), leading_icon=ft.Icons.ADD))
        if self.saved.value not in {i["call"] for i in items} | {NEW}:
            self.saved.value = NEW if not items else None  # nothing saved yet: straight to a new station
        self._show_new()

    def _show_new(self) -> None:
        """The callsign and path fields only for a new station; a saved one has them already."""
        self.new_row.visible = self.saved.value == NEW
        self.remove_btn.visible = self.saved.value not in (None, NEW)

    def _pick(self, e) -> None:
        """Choosing a saved station fills in its callsign and path, ready to connect."""
        item = next((i for i in self.engine.config.saved_bbs() if i["call"] == e.control.value), None)
        if item:
            self.remote.value, self.path.value = item["call"], item["path"]
        elif e.control.value == NEW:
            self.remote.value = self.path.value = ""
        self._reload_lines()
        self.refresh()
        self._show_new()
        self.app.page.update()

    def _save(self, _e) -> None:
        if not self.current:
            return
        self.engine.config.save_bbs(self.current, self.path.value or "")
        self.app.save_config_soon()
        self.saved.value = self.current
        self._fill_saved()
        self.app.toast(self.t("bbs_saved_as", call=self.current))
        self.app.page.update()

    def _remove(self, _e) -> None:
        if self.saved.value:
            self.engine.config.remove_bbs(self.saved.value)
            self.app.save_config_soon()
            self.saved.value = None
            self._fill_saved()
            self.app.page.update()

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
        info = self.engine.session_info(self.current) if state else None
        connecting = state == "connecting"
        if info and info.get("via") == "vara":
            flags = " · PTT" if info.get("ptt") else ""
            flags += f" · TX {info['buffer']} B" if info.get("buffer") else ""
            self.state.value = f"{self.current}: VARA FM · {self.t('vara_' + state)}{flags}"
        elif connecting and info:
            hms = lambda ts: time.strftime("%H:%M:%S", time.localtime(ts))  # noqa: E731
            self.state.value = f"{self.current}: " + self.t("term_attempt", n=info["attempts"], max=info["max_attempts"],
                                                            time=hms(info["last_attempt"]), start=hms(info["started"]))
        else:
            self.state.value = f"{self.current}: {state}" if state else self.t("not_connected_session")
        self.state.color = (ft.Colors.GREEN if state == "connected" else ft.Colors.AMBER_800 if connecting
                            else ft.Colors.ON_SURFACE_VARIANT)
        # While it keeps trying, the Disconnect button becomes a clear "Stop connecting".
        self.disconnect_btn.disabled = not state
        self.disconnect_btn.tooltip = self.t("term_stop") if connecting else self.t("disconnect")
        self.disconnect_btn.icon = ft.Icons.STOP_CIRCLE if connecting else ft.Icons.LINK_OFF
        self.disconnect_btn.icon_color = ft.Colors.ERROR if connecting or state == "connected" else None
        self.connect_btn.disabled = bool(state)
        self.input.disabled = state != "connected"

    def _reload_lines(self) -> None:
        self.lines.controls = []
        self._open = None
        for e in self.engine.terminal:
            if e["remote"] == self.current:
                self._add(e)

    async def _connect(self, _e) -> None:
        try:
            self.engine.connect(self.current, self.path.value or "",
                                via=self.via.value if self.via.visible else "ax25")
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
        """Disconnect, or stop the connect attempts while the station has not answered yet."""
        try:
            self.engine.disconnect(self.current)
        except ValueError as err:
            self.app.toast(str(err), error=True)
        self.refresh()
        self.app.page.update()

    async def _send(self, _e) -> None:
        text = self.input.value or ""
        try:
            self.engine.send_text(self.current, text + "\n")
        except (ConnectionError, ValueError) as err:
            self.app.toast(f"{self.t('not_sent')}: {err}", error=True)
            return
        self.input.value = ""
        await self.input.focus()
