"""Bulletins: APRS messages to everybody (BLN0–9 news, BLNA–Z announcements, group bulletins, weather alerts)
from the stations around us, and our own, repeated by themselves until they run out."""

from __future__ import annotations

import time

import flet as ft

from aprs_kiss_core import bulletins as bln
from aprs_kiss_core import units

from .base import View, ViaPicker, message_text

KM_CHOICES = (50, 150, 500, 0)  # the board's distance (0 = all); shown in the user's unit
KIND_COLORS = {"bulletin": ft.Colors.PRIMARY, "group": ft.Colors.TEAL, "announcement": ft.Colors.DEEP_PURPLE,
               "nws": ft.Colors.RED_700}


def copies(kind: str, hours: float) -> int:
    """How many times ours goes out in `hours` (for the dialog: what it costs on air)."""
    board = bln.Board()
    e = board.start("BLNA" if kind == "announcement" else "BLN1", "x", "radio", hours, 0)
    now = 0.0
    while board.due(now):
        board.sent(e, now)
        now = e["next"]
    return e["sent"]


class BulletinsView(View):
    key = "bulletins"
    icon = ft.Icons.CAMPAIGN_OUTLINED
    selected_icon = ft.Icons.CAMPAIGN

    def build(self) -> ft.Control:
        self._signature = None
        self._fresh: set[tuple[str, str]] = set()  # unread when the screen was opened: marked as new
        self.title = ft.Text(size=15, weight=ft.FontWeight.BOLD, expand=True)
        self.reach = ft.PopupMenuButton(icon=ft.Icons.TUNE, tooltip=self.t("bln_reach"), items=[
            ft.PopupMenuItem(content=ft.Text(self._reach_text(km)), on_click=lambda _e, km=km: self._set_reach(km))
            for km in KM_CHOICES])
        header = ft.Container(
            ft.Row([ft.Icon(ft.Icons.CAMPAIGN, color=ft.Colors.PRIMARY), self.title, self.reach,
                    ft.IconButton(ft.Icons.INFO_OUTLINE, tooltip=self.t("about"), on_click=self._info)],
                   spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.only(left=12, right=4, top=4, bottom=4), border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
        )
        self.feed = ft.ListView(expand=True, spacing=8, padding=ft.Padding.all(12))
        self.new_btn = ft.FilledButton(self.t("bln_new"), icon=ft.Icons.ADD, on_click=self._compose)
        return ft.Column([
            header,
            ft.Container(ft.SelectionArea(self.feed), expand=True, border_radius=8,
                         bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
            ft.Row([self.new_btn], alignment=ft.MainAxisAlignment.END),
        ], expand=True)

    def _reach_text(self, km: int) -> str:
        return self.t("bln_all") if not km else self.t("bln_within", dist=units.current.whole(km))

    def _set_reach(self, km: int) -> None:
        self.engine.config.bulletin_km = km
        self.app.save_config_soon()
        self._signature = None
        self.refresh()
        self.app.page.update()

    def on_event(self, kind, data) -> None:
        if kind == "bulletin":
            self._signature = None

    def shown(self) -> None:
        """Opened: what was unread is marked new on the screen, and read for the badge."""
        self._fresh = {(e["from"], e["addressee"]) for e in self.engine.bulletins_shown() if not e.get("read")}
        self.engine.bulletins_read()
        self._signature = None

    def refresh(self) -> None:
        eng = self.engine
        now = time.time()
        shown = eng.bulletins_shown()
        if self.app.current_key == self.key:  # came while on screen: new here, read for the badge
            arrived = {(e["from"], e["addressee"]) for e in shown if not e.get("read")}
            if arrived:
                self._fresh |= arrived
                eng.bulletins_read()
        mine = list(eng.board.mine)
        signature = (tuple((e["from"], e["addressee"], e["text"], e.get("count"), e.get("km")) for e in shown),
                     tuple((m["addressee"], m["sent"], m["text"]) for m in mine), int(now // 30),
                     eng.config.bulletin_km, units.current.miles)
        if signature == self._signature:
            return
        self._signature = signature
        km = int(eng.config.bulletin_km or 0)
        self.title.value = self.t("bln_title_all") if not km else self.t("bln_title", dist=units.current.whole(km))
        controls: list[ft.Control] = []
        if mine:
            controls.append(ft.Text(self.t("bln_mine"), size=12, weight=ft.FontWeight.W_600,
                                    color=ft.Colors.ON_SURFACE_VARIANT))
            controls += [self._mine_card(m, now) for m in mine]
            controls.append(ft.Text(self.t("bln_heard"), size=12, weight=ft.FontWeight.W_600,
                                    color=ft.Colors.ON_SURFACE_VARIANT))
        controls += [self._card(e, now) for e in shown]
        if not shown:
            hidden = len(eng.board.heard)
            controls.append(ft.Text(self.t("bln_empty_hidden", n=hidden) if hidden else self.t("bln_empty"),
                                    color=ft.Colors.ON_SURFACE_VARIANT))
        self.feed.controls = controls

    def _chip(self, addr: str, kind: str) -> ft.Control:
        color = KIND_COLORS.get(kind, ft.Colors.PRIMARY)
        label = addr if kind != "announcement" else f"{addr} · {self.t('bln_kind_announcement')}"
        return ft.Container(ft.Text(label, size=11, weight=ft.FontWeight.BOLD, color=color),
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2), border_radius=10,
                            bgcolor=ft.Colors.with_opacity(0.12, color))

    def _card(self, e: dict, now: float) -> ft.Control:
        meta = [self.t.age(now - e["time"])]
        if e.get("km") is not None:
            meta.append(units.current.distance_short(e["km"]))
        meta.append(self.t("via_radio") if e.get("via") == "radio" else self.t("via_internet"))
        if e.get("count", 1) > 1:
            meta.append(self.t("bln_heard_times", n=e["count"]))
        new = (e["from"], e["addressee"]) in self._fresh
        sender = ft.TextButton(e["from"], on_click=lambda _e, c=e["from"]: self.app.show_station(c),
                               style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=4)))
        head = [self._chip(e["addressee"], e.get("kind", "")), sender, ft.Container(expand=True)]
        if new:
            head.append(ft.Container(ft.Text(self.t("bln_new_badge"), size=10, color=ft.Colors.ON_PRIMARY,
                                             weight=ft.FontWeight.BOLD),
                                     bgcolor=ft.Colors.PRIMARY, border_radius=8,
                                     padding=ft.Padding.symmetric(horizontal=6, vertical=1)))
        head.append(ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, icon_size=18, items=[
            ft.PopupMenuItem(content=ft.Text(self.t("bln_reply")), icon=ft.Icons.REPLY,
                             on_click=lambda _e, c=e["from"]: self._reply(c)),
            ft.PopupMenuItem(content=ft.Text(self.t("bbs_delete")), icon=ft.Icons.DELETE_OUTLINE,
                             on_click=lambda _e, s=e["from"], a=e["addressee"]: self._delete(s, a)),
        ]))
        return ft.Container(
            ft.Column([ft.Row(head, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                       message_text(self.app, e["text"], size=15),
                       ft.Text(" · ".join(meta), size=11, color=ft.Colors.ON_SURFACE_VARIANT)], spacing=4, tight=True),
            padding=ft.Padding.only(left=12, right=4, top=6, bottom=10), border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.all(1, ft.Colors.PRIMARY) if new else None,
        )

    def _mine_card(self, m: dict, now: float) -> ft.Control:
        left = max(0, m["until"] - now)
        info = self.t("bln_sent_times", n=m["sent"])
        if m.get("next") and m["next"] > now:
            info += " · " + self.t("bln_next_in", t=f"{max(1, round((m['next'] - now) / 60))} min")
        info += " · " + self.t("bln_until", when=time.strftime("%H:%M", time.localtime(m["until"])))
        return ft.Container(
            ft.Column([
                ft.Row([self._chip(m["addressee"], m.get("kind", "")), ft.Container(expand=True),
                        ft.TextButton(self.t("bln_stop"), icon=ft.Icons.STOP_CIRCLE_OUTLINED,
                                      on_click=lambda _e, a=m["addressee"]: self._stop(a))],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(m["text"], size=15),
                ft.ProgressBar(value=1 - left / max(1, m["until"] - m["created"]), height=3,
                               color=ft.Colors.PRIMARY, bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.PRIMARY)),
                ft.Text(info, size=11, color=ft.Colors.ON_SURFACE_VARIANT),
            ], spacing=6, tight=True),
            padding=ft.Padding.only(left=12, right=4, top=6, bottom=10), border_radius=12,
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
        )

    def _reply(self, call: str) -> None:
        self.app.view("messages").compose_to(call)
        self.app.select("messages")

    def _stop(self, addr: str) -> None:
        self.engine.stop_bulletin(addr)
        self._signature = None
        self.refresh()
        self.app.page.update()

    def _delete(self, sender: str, addr: str) -> None:
        self.engine.delete_bulletin(sender, addr)
        self._signature = None
        self.refresh()
        self.app.page.update()

    # ─── a new one ───────────────────────────────────────────────────────

    def _compose(self, _e=None) -> None:
        t = self.t
        taken = {m["addressee"] for m in self.engine.board.mine}
        kind = ft.Dropdown(label=t("bln_kind"), value="bulletin", width=380, options=[
            ft.DropdownOption(key="bulletin", text=t("bln_kind_bulletin")),
            ft.DropdownOption(key="announcement", text=t("bln_kind_announcement_long"))])
        line = ft.Dropdown(label=t("bln_line"), width=110)
        group = ft.TextField(label=t("bln_group"), hint_text="WX, CLUB…", width=240, max_length=5,
                             capitalization=ft.TextCapitalization.CHARACTERS)
        text = ft.TextField(label=t("text"), max_length=bln.MAX_TEXT, multiline=True, min_lines=2, max_lines=3,
                            width=520, autofocus=True)
        hours = ft.Dropdown(label=t("bln_hours"), width=200)
        via = ViaPicker(self.app, "bulletin_via", lambda: "both" if self.engine.config.beacon_is else "radio")
        preview = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT, font_family="monospace", selectable=True)
        error = ft.Text(color=ft.Colors.ERROR, visible=False)

        def addr() -> str:
            try:
                return bln.addressee(line.value or "", "" if kind.value == "announcement" else (group.value or ""))
            except ValueError:
                return ""

        def update_preview(_e=None) -> None:
            a = addr() or "BLN?"
            n = copies(kind.value, float(hours.value or 4))
            preview.value = (f":{a.ljust(9)}:{(text.value or '').strip()}\n"
                             + t("bln_copies", n=n, h=hours.value or 4)
                             + (f"\n{t('bln_replaces')}" if a in taken else ""))
            self.app.page.update()

        def set_kind(_e=None, update=True) -> None:
            ann = kind.value == "announcement"
            chars = bln.LINES[10:] if ann else bln.LINES[:10]
            line.options = [ft.DropdownOption(key=c, text=c) for c in chars]
            line.value = next((c for c in chars if f"BLN{c}" not in taken), chars[0])
            group.visible = not ann
            hours.options = [ft.DropdownOption(key=str(h), text=t("bln_hours_n", n=h)) for h in bln.HOURS]
            hours.value = str(bln.DEFAULT_HOURS[kind.value])
            if update:
                update_preview()

        kind.on_select = set_kind
        for c in (line, hours):
            c.on_select = update_preview
        for c in (group, text):
            c.on_change = update_preview
        set_kind(update=False)

        async def send(_e) -> None:
            a = addr()
            body = (text.value or "").strip()
            if not a or not body:
                error.value, error.visible = t("bln_missing"), True
                self.app.page.update()
                return
            g = "" if kind.value == "announcement" else (group.value or "")
            ok = await self.app.guard(self.engine.send_bulletin(line.value, g, body, via.value(),
                                                                float(hours.value or 4)))
            if ok:
                self.app.page.pop_dialog()
                self._signature = None
                self.refresh()
                self.app.toast(t("bln_sent", addr=a))
                self.app.page.update()

        update_preview_text = t("bln_compose_hint")
        self.app.show_dialog(ft.AlertDialog(
            title=ft.Text(t("bln_new")),
            content=ft.Column([
                ft.Text(update_preview_text, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row([kind, line], wrap=True),
                ft.Row([group, hours], wrap=True),
                text,
                ft.Row([ft.Text(t("via"), size=13), via.control], tight=True, visible=via.control.visible),
                preview, error,
            ], tight=True, spacing=10, width=520, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton(t("cancel"), on_click=lambda _e: self.app.page.pop_dialog()),
                     ft.FilledButton(t("bln_send"), icon=ft.Icons.CAMPAIGN, on_click=send)],
        ))
        update_preview()

    def _info(self, _e=None) -> None:
        self.app.show_dialog(ft.AlertDialog(
            title=ft.Text(self.t("bulletins")),
            content=ft.Column([ft.Text(self.t("bln_about"), size=13),
                               ft.Text(self.t("bln_about_reach"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)],
                              tight=True, spacing=8, width=520),
            actions=[ft.TextButton(self.t("close"), on_click=lambda _e: self.app.page.pop_dialog())],
        ))
