"""#APRSThursday: the weekly HOTG net through ANSRVR, with its own feed apart from the inbox."""

from __future__ import annotations

import time

import flet as ft

from aprs_kiss_core import thursday

from .base import View, ViaPicker, clock, message_text
from .messages import STATE_ICONS


def duration(seconds: float) -> str:
    """'2 d 5 h', '3 h 12 min', '7 min'."""
    s = max(0, int(seconds))
    d, h, m = s // 86400, s % 86400 // 3600, s % 3600 // 60
    if d:
        return f"{d} d {h} h"
    if h:
        return f"{h} h {m} min"
    return f"{max(m, 1)} min"


def local_time(ts: float) -> str:
    return time.strftime("%d.%m. %H:%M", time.localtime(ts))


class ThursdayView(View):
    key = "thursday"
    icon = ft.Icons.EVENT_OUTLINED
    selected_icon = ft.Icons.EVENT

    def build(self) -> ft.Control:
        self._signature = None
        self.status = ft.Text(size=15, weight=ft.FontWeight.BOLD, expand=True)
        self.member = ft.Text(color=ft.Colors.ON_SURFACE_VARIANT)
        self.wait = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)
        self.feed = ft.ListView(expand=True, spacing=8, auto_scroll=True, auto_scroll_animation=0, padding=ft.Padding.all(12))
        self.text = ft.TextField(hint_text=self.t("th_placeholder"), expand=True, dense=True,
                                 max_length=thursday.MAX_TEXT, on_submit=self._send)
        compact = self.app.compact
        self.via_picker = ViaPicker(self.app, "thursday_via", lambda: "internet")  # remembered, as in Messages
        self.via = self.via_picker.control
        self.send_btn = (ft.IconButton(ft.Icons.SEND, tooltip=self.t("th_send"), on_click=self._send,
                                       style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY))
                         if compact else ft.FilledButton(self.t("th_send"), icon=ft.Icons.SEND, on_click=self._send))
        self.leave_btn = ft.TextButton(self.t("th_leave"), icon=ft.Icons.LOGOUT, on_click=self._leave)
        # one short line: when it starts (or ends); what it is, the group and the map are behind the "i"
        header = ft.Container(
            ft.Row([ft.Icon(ft.Icons.EVENT, color=ft.Colors.PRIMARY), self.status,
                    ft.IconButton(ft.Icons.INFO_OUTLINE, tooltip=self.t("about"), on_click=self._info)],
                   spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.only(left=12, right=4, top=4, bottom=4), border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
        )
        return ft.Column(
            [
                header,
                ft.Container(ft.SelectionArea(self.feed), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
                ft.Row([self.text, self.via, self.send_btn], vertical_alignment=ft.CrossAxisAlignment.START),
                self.wait,
            ],
            expand=True,
        )

    def on_event(self, kind, data) -> None:
        if kind == "thursday":
            self._signature = None

    def refresh(self) -> None:
        now = time.time()
        eng = self.engine
        start, end = thursday.window(now)
        until = eng.thursday_member_until(now)
        wait = eng.thursday_wait(now)
        states = tuple(eng.message_state(e.get("msg_no")) for e in eng.thursday if e.get("msg_no"))
        signature = (len(eng.thursday), states, int(now // 30), bool(until), int(wait // 30),
                     eng.aprsis is not None)
        if signature == self._signature:
            return
        self._signature = signature
        if thursday.is_active(now):
            self.status.value = self.t("th_running", t=duration(end - now))
        else:
            self.status.value = self.t("th_starts_in", t=duration(start - now))
            self.status.tooltip = self.t("th_next", when=local_time(start), t=duration(start - now))
        self.member.value = (self.t("th_member", when=local_time(until)) if until
                             else self.t("th_not_member"))
        self.leave_btn.visible = bool(until)
        self.wait.visible = bool(wait)
        self.wait.value = self.t("th_wait", t=duration(wait)) if wait else ""
        self.send_btn.disabled = bool(wait)
        self.via_picker.sync()
        self.feed.controls = [self._bubble(e) for e in eng.thursday] or [
            ft.Text(self.t("th_empty"), color=ft.Colors.ON_SURFACE_VARIANT)]

    def _bubble(self, e: dict) -> ft.Control:
        kind = e.get("kind")
        out = kind in ("out", "leave")
        meta: list[ft.Control] = [ft.Text(clock(e["time"]), size=11, color=ft.Colors.ON_SURFACE_VARIANT)]
        if e.get("via") in ("radio", "internet", "both"):
            meta.append(ft.Text(self.t(f"via_{e['via']}"), size=11, color=ft.Colors.ON_SURFACE_VARIANT))
        if out:
            state = self.engine.message_state(e.get("msg_no"))
            if state in STATE_ICONS:
                icon, color = STATE_ICONS[state]
                meta.append(ft.Icon(icon, size=14, color=color, tooltip=self.t(f"state_{state}")))
        if kind == "server":
            return ft.Row([ft.Text(f"{e['from']}: {e['text']}", size=12, italic=True,
                                   color=ft.Colors.ON_SURFACE_VARIANT), *meta], spacing=6, wrap=True)
        sender = [] if out else [ft.Text(e["from"], weight=ft.FontWeight.BOLD, size=12,
                                         color=ft.Colors.PRIMARY)]
        bubble = ft.Container(
            ft.Column([*sender, message_text(self.app, e["text"]), ft.Row(meta, spacing=6, tight=True)],
                      spacing=2, tight=True),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8), border_radius=12,
            bgcolor=ft.Colors.PRIMARY_CONTAINER if out else ft.Colors.SURFACE_CONTAINER_HIGH,
        )
        return ft.Row([bubble], alignment=ft.MainAxisAlignment.END if out else ft.MainAxisAlignment.START)

    def _via(self) -> str:
        return self.via_picker.value()

    async def _send(self, _e) -> None:
        text = (self.text.value or "").strip()
        if not text:
            return
        if await self.app.guard(self.engine.send_thursday(text, self._via())):
            self.text.value = ""
            self._signature = None
            self.refresh()
            self.app.page.update()

    def _info(self, _e=None) -> None:
        """What APRS Thursday is, whether we are in the group, the map; leaving the group."""
        now = time.time()
        start, _end = thursday.window(now)
        self.leave_btn.on_click = self._leave_from_dialog
        self.app.show_dialog(ft.AlertDialog(
            title=ft.Text("#APRSThursday"),
            content=ft.Column([
                ft.Text(self.t("th_next", when=local_time(start), t=duration(start - now)), weight=ft.FontWeight.BOLD)
                if not thursday.is_active(now) else ft.Text(self.status.value, weight=ft.FontWeight.BOLD),
                self.member,
                ft.Text(self.t("th_about"), size=13),
                ft.Text(self.t("th_rf_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row([ft.TextButton(self.t("th_map"), icon=ft.Icons.MAP_OUTLINED, url=thursday.MAP_URL),
                        self.leave_btn], wrap=True),
            ], tight=True, spacing=8, width=520),
            actions=[ft.TextButton(self.t("close"), on_click=lambda _e: self.app.page.pop_dialog())],
        ))

    async def _leave_from_dialog(self, e) -> None:
        self.app.page.pop_dialog()
        await self._leave(e)

    async def _leave(self, _e) -> None:
        if await self.app.guard(self.engine.leave_thursday(self._via())):
            self._signature = None
            self.refresh()
            self.app.page.update()
