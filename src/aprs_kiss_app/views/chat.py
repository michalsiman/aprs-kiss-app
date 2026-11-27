"""Packet chat: plain text in UI frames to CQ."""

from __future__ import annotations

import flet as ft

from aprs_kiss_core.geotext import find_positions, write_position

from .base import View, capped_append, clock

LIMIT = 500


class ChatView(View):
    key = "chat"
    icon = ft.Icons.FORUM_OUTLINED
    selected_icon = ft.Icons.FORUM

    def build(self) -> ft.Control:
        self.lines = ft.ListView(expand=True, spacing=6, auto_scroll=True, auto_scroll_animation=0, padding=ft.Padding.all(8))
        for entry in self.engine.chat:
            self.lines.controls.append(self._entry(entry))
        self.input = ft.TextField(hint_text=self.t("type_here"), expand=True, on_submit=self._send, dense=True)
        return ft.Column(
            [
                ft.Text(self.t("chat_hint"), color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Container(ft.SelectionArea(self.lines), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
                ft.Row([ft.IconButton(ft.Icons.MY_LOCATION, tooltip=self.t("pos_send_mine"), on_click=self._send_mine),
                        self.input, ft.IconButton(ft.Icons.SEND, tooltip=self.t("send"), on_click=self._send)]),
            ],
            expand=True,
        )

    def _entry(self, e: dict) -> ft.Control:
        return ft.Row(
            [
                ft.Text(clock(e["time"]), size=11, color=ft.Colors.ON_SURFACE_VARIANT, width=64),
                ft.Text(e["from"], weight=ft.FontWeight.BOLD, width=96,
                        color=ft.Colors.ORANGE if e.get("out") else ft.Colors.PRIMARY),
                ft.Text(e["text"], expand=True),
                *[ft.IconButton(ft.Icons.MAP_OUTLINED, icon_size=18, tooltip=self.t("pos_on_map"),
                                on_click=lambda _e, p=p, who=e["from"]: self.app.page.run_task(self.app.show_point, *p, who))
                  for p in find_positions(e["text"])[:1]],
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def on_event(self, kind, data) -> None:
        if kind == "chat":
            capped_append(self.lines, self._entry(data["entry"]), LIMIT)

    async def _send_mine(self, _e) -> None:
        """Where we are (GPS or typed in) to everybody on the frequency."""
        here = self.engine.my_position()
        if not here:
            self.app.toast(self.t("no_position"), error=True)
            return
        await self.app.guard(self.engine.send_chat(write_position(*here)))

    async def _send(self, _e) -> None:
        text = (self.input.value or "").strip()
        if not text:
            return
        if await self.app.guard(self.engine.send_chat(text)):
            self.input.value = ""
        await self.input.focus()
