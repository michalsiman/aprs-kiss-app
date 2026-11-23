"""APRS messages: conversations by callsign, sending with acknowledgement."""

from __future__ import annotations

import flet as ft

from .base import View, clock

MAX_TEXT = 67  # APRS message text limit
STATE_ICONS = {
    "pending": (ft.Icons.SCHEDULE, ft.Colors.ON_SURFACE_VARIANT),
    "acked": (ft.Icons.DONE_ALL, ft.Colors.GREEN),
    "rejected": (ft.Icons.BLOCK, ft.Colors.RED),
    "failed": (ft.Icons.ERROR_OUTLINE, ft.Colors.RED),
}


class MessagesView(View):
    key = "messages"
    icon = ft.Icons.MAIL_OUTLINE
    selected_icon = ft.Icons.MAIL

    def build(self) -> ft.Control:
        self.selected: str | None = None
        self.unread: set[str] = set()
        self._signature = None
        self.conversations = ft.ListView(expand=True, spacing=2)
        self.thread = ft.ListView(expand=True, spacing=8, auto_scroll=True, padding=ft.Padding.all(12))
        self.title = ft.Text(self.t("pick_conversation"), size=16, weight=ft.FontWeight.BOLD)
        compact = self.app.compact
        # Writing: who to (a new message only), the text, then the way, the characters left and Send -
        # each on its own line, wide enough to read on a phone.
        self.to = ft.TextField(label=self.t("to"), dense=not compact, visible=False,
                               capitalization=ft.TextCapitalization.CHARACTERS)
        self.text = ft.TextField(hint_text=self.t("text"), dense=not compact, on_submit=self._send,
                                 multiline=True, min_lines=1, max_lines=3, shift_enter=True,
                                 on_change=self._count)
        self.count = ft.Text(f"0/{MAX_TEXT}", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.via = ft.Dropdown(
            width=120 if compact else 200, dense=True, value="both",
            options=[ft.DropdownOption(key=k, text=self.t(f"via_{k}")) for k in ("radio", "internet", "both")],
        )
        # On a phone one side at a time: the conversations, or one conversation with a back button.
        self.back = ft.IconButton(ft.Icons.ARROW_BACK, tooltip=self.t("back"), on_click=self._back, visible=False)
        self.left = left = ft.Column(
            [
                ft.FilledTonalButton(self.t("new_message"), icon=ft.Icons.EDIT, on_click=self._new),
                self.conversations,
            ],
            width=None if compact else 250,
            expand=compact,
        )
        self.right = right = ft.Column(
            [
                ft.Row([self.back, self.title], spacing=4),
                ft.Container(ft.SelectionArea(self.thread), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
                self.to,
                self.text,
                ft.Row([self.via, ft.Container(expand=True), self.count,
                        ft.IconButton(ft.Icons.SEND, tooltip=self.t("send"), on_click=self._send,
                                      style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY))],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,  # "to" and the text as wide as the screen
        )
        if compact:
            return ft.Row([left, right], expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        return ft.Row([left, ft.VerticalDivider(width=1), right], expand=True,
                      vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    def _count(self, _e=None) -> None:
        """Characters used of the APRS limit; longer text is cut to it."""
        text = self.text.value or ""
        if len(text) > MAX_TEXT:
            self.text.value = text = text[:MAX_TEXT]
        self.count.value = f"{len(text)}/{MAX_TEXT}"
        self.count.color = ft.Colors.ERROR if len(text) >= MAX_TEXT else ft.Colors.ON_SURFACE_VARIANT
        self.app.page.update()

    # ─── data ─────────────────────────────────────────────────────────────

    def _party(self, m: dict) -> str:
        return (m["from"] if m["direction"] == "in" else m["to"]).upper()

    def _grouped(self) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = {}
        for m in self.engine.messages:
            groups.setdefault(self._party(m), []).append(m)
        return dict(sorted(groups.items(), key=lambda kv: -kv[1][-1]["time"]))

    # ─── events ───────────────────────────────────────────────────────────

    def on_event(self, kind, data) -> None:
        if kind == "message":
            sender = data["from"].upper()
            if not (self.app.current_key == self.key and self.selected == sender):
                self.unread.add(sender)

    def open_conversation(self, call: str) -> None:
        self.selected = call.upper()
        self.to.visible = False
        self.unread.discard(self.selected)
        self._signature = None
        self.refresh()

    def refresh(self) -> None:
        if self.app.current_key == self.key and self.selected:
            self.unread.discard(self.selected)
        groups = self._grouped()
        states = tuple(self.engine.message_state(m.get("msg_no")) for m in self.engine.messages
                       if m["direction"] == "out")
        signature = (len(self.engine.messages), self.selected, states, tuple(sorted(self.unread)),
                     self.engine.aprsis is not None)
        if signature == self._signature:
            return
        self._signature = signature
        self.via.visible = self.engine.aprsis is not None
        self.conversations.controls = [self._conversation_tile(call, msgs) for call, msgs in groups.items()]
        if not groups:
            self.conversations.controls = [ft.Text(self.t("no_messages"), color=ft.Colors.ON_SURFACE_VARIANT)]
        if self.selected:
            self.title.value = self.selected
            self.thread.controls = [self._bubble(m) for m in groups.get(self.selected, [])]
        elif self.to.visible:
            self.title.value = self.t("new_message")
            self.thread.controls = []
        else:
            self.title.value = self.t("pick_conversation")
            self.thread.controls = []
        self._sides()

    def _sides(self) -> None:
        if not self.app.compact:
            return
        open_ = bool(self.selected or self.to.visible)
        self.left.visible, self.right.visible, self.back.visible = not open_, open_, open_

    def _back(self, _e) -> None:
        self.selected = None
        self.to.visible = False
        self._signature = None
        self.refresh()
        self.app.page.update()

    def _conversation_tile(self, call: str, msgs: list[dict]) -> ft.Control:
        last = msgs[-1]
        unread = call in self.unread
        return ft.ListTile(
            leading=ft.Icon(ft.Icons.MARK_EMAIL_UNREAD if unread else ft.Icons.PERSON,
                            color=ft.Colors.PRIMARY if unread else None),
            title=ft.Text(call, weight=ft.FontWeight.BOLD if unread else None),
            subtitle=ft.Text(last["text"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            trailing=ft.Text(clock(last["time"]), size=11),
            selected=call == self.selected,
            dense=True,
            on_click=lambda _e, c=call: self.open_conversation(c),
        )

    def _bubble(self, m: dict) -> ft.Control:
        out = m["direction"] == "out"
        meta: list[ft.Control] = [ft.Text(clock(m["time"]), size=11, color=ft.Colors.ON_SURFACE_VARIANT)]
        if m.get("via"):
            meta.append(ft.Text(self.t(f"via_{m['via']}") if m["via"] in ("radio", "internet", "both") else m["via"],
                                size=11, color=ft.Colors.ON_SURFACE_VARIANT))
        if out:
            state = self.engine.message_state(m.get("msg_no"))
            if state in STATE_ICONS:
                icon, color = STATE_ICONS[state]
                meta.append(ft.Icon(icon, size=14, color=color, tooltip=self.t(f"state_{state}")))
        bubble = ft.Container(
            ft.Column([ft.Text(m["text"], selectable=True), ft.Row(meta, spacing=6, tight=True)], spacing=2, tight=True),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=12,
            bgcolor=ft.Colors.PRIMARY_CONTAINER if out else ft.Colors.SURFACE_CONTAINER_HIGH,
        )
        return ft.Row([bubble], alignment=ft.MainAxisAlignment.END if out else ft.MainAxisAlignment.START)

    # ─── actions ──────────────────────────────────────────────────────────

    async def _new(self, _e) -> None:
        self.selected = None
        self.to.visible = True
        self.to.value = ""
        self._signature = None
        self.refresh()
        await self.to.focus()

    def compose_to(self, call: str) -> None:
        if any(self._party(m) == call.upper() for m in self.engine.messages):
            self.open_conversation(call)
            return
        self.selected = None
        self.to.visible = True
        self.to.value = call.upper()
        self._signature = None
        self.refresh()

    async def _send(self, _e) -> None:
        to = (self.to.value if self.to.visible else self.selected or "").strip().upper()
        text = (self.text.value or "").strip()
        if not to or not text:
            return
        via = self.via.value if self.via.visible else "radio"
        if await self.app.guard(self.engine.send_aprs_message(to, text, via)):
            self.text.value = ""
            self.count.value, self.count.color = f"0/{MAX_TEXT}", ft.Colors.ON_SURFACE_VARIANT
            self.open_conversation(to)
        await self.text.focus()
