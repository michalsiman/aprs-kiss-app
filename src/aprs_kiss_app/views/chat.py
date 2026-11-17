"""Packet chat: plain text in UI frames to CQ."""

from __future__ import annotations

import flet as ft

from .base import View, capped_append, clock

LIMIT = 500


class ChatView(View):
    key = "chat"
    icon = ft.Icons.FORUM_OUTLINED
    selected_icon = ft.Icons.FORUM

    def build(self) -> ft.Control:
        self.lines = ft.ListView(expand=True, spacing=6, auto_scroll=True, padding=ft.Padding.all(8))
        for entry in self.engine.chat:
            self.lines.controls.append(self._entry(entry))
        self.input = ft.TextField(hint_text=self.t("type_here"), expand=True, on_submit=self._send, dense=True)
        return ft.Column(
            [
                ft.Text(self.t("chat_hint"), color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Container(ft.SelectionArea(self.lines), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
                ft.Row([self.input, ft.IconButton(ft.Icons.SEND, tooltip=self.t("send"), on_click=self._send)]),
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
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def on_event(self, kind, data) -> None:
        if kind == "chat":
            capped_append(self.lines, self._entry(data["entry"]), LIMIT)

    async def _send(self, _e) -> None:
        text = (self.input.value or "").strip()
        if not text:
            return
        if await self.app.guard(self.engine.send_chat(text)):
            self.input.value = ""
        await self.input.focus()
