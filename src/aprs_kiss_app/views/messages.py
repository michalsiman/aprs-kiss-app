"""APRS messages: conversations by callsign, sending with acknowledgement."""

from __future__ import annotations

import json
import re
import time

import flet as ft

from aprs_kiss_core.aprs import MAX_MESSAGE_PARTS, message_parts
from aprs_kiss_core.geotext import find_positions, write_position
from aprs_kiss_core.services import SERVICES
from aprs_kiss_core.spotting import CAMILLA, GATEWAY_NAMES, MODES, PROGRAMS, Spot, SpotError, build as build_spot, default_gateway, gateways_for

from .base import View, bearing, clock, distance_km, toggle

MAX_TEXT = 67  # APRS message text limit
STATE_ICONS = {
    "pending": (ft.Icons.SCHEDULE, ft.Colors.ON_SURFACE_VARIANT),
    "acked": (ft.Icons.DONE_ALL, ft.Colors.GREEN),
    "rejected": (ft.Icons.BLOCK, ft.Colors.RED),
    "failed": (ft.Icons.ERROR_OUTLINE, ft.Colors.RED),
}
# the colour of a conversation's circle, chosen by its letter (white letter on each)
AVATAR_COLORS = (ft.Colors.RED_700, ft.Colors.INDIGO_500, ft.Colors.GREEN_700, ft.Colors.PURPLE_600,
                 ft.Colors.ORANGE_800, ft.Colors.TEAL_700, ft.Colors.PINK_600, ft.Colors.BLUE_700,
                 ft.Colors.BROWN_500, ft.Colors.DEEP_PURPLE_400, ft.Colors.CYAN_800, ft.Colors.DEEP_ORANGE_700,
                 ft.Colors.LIGHT_GREEN_800, ft.Colors.BLUE_GREY_600)


def avatar_letter(call: str) -> str:
    """The letter in the circle: the suffix's first (OK1TNT → T: the prefix is the same for a whole
    country), the first character for a name without a number (REPEAT → R)."""
    base = call.split("-")[0].upper()
    m = re.search(r"\d([A-Z])[A-Z]*$", base)
    return m.group(1) if m else (base[:1] or "?")


def avatar_color(letter: str) -> str:
    return AVATAR_COLORS[ord(letter[:1] or "?") % len(AVATAR_COLORS)]


class MessagesView(View):
    key = "messages"
    icon = ft.Icons.MAIL_OUTLINE
    selected_icon = ft.Icons.MAIL

    def build(self) -> ft.Control:
        self.selected: str | None = None
        self.unread: dict[str, int] = self._load_unread()  # callsign → how many messages unread
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
        # How a message goes: two on/off icons, the radio and the internet (one or both); remembered
        via = self._saved_via()
        self.via_radio = toggle(ft.Icons.SETTINGS_INPUT_ANTENNA, ft.Icons.SETTINGS_INPUT_ANTENNA,
                                via in ("radio", "both"), self.t("via_radio"), lambda _e: self._flip_via("radio"))
        self.via_net = toggle(ft.Icons.PUBLIC, ft.Icons.PUBLIC, via in ("internet", "both"), self.t("via_internet"),
                              lambda _e: self._flip_via("internet"))
        for b in (self.via_radio, self.via_net):  # off: faint; on: the accent colour on a tint
            b.icon_color = ft.Colors.with_opacity(0.35, ft.Colors.ON_SURFACE)
            b.selected_icon_color = ft.Colors.PRIMARY
        self.via = ft.Row([self.via_radio, self.via_net], spacing=2, tight=True)
        # On a phone one side at a time: the conversations, or one conversation with a back button.
        self.back = ft.IconButton(ft.Icons.ARROW_BACK, tooltip=self.t("back"), on_click=self._back, visible=False)
        # where the other station is: how far from us, and a button to see it on the map
        self.where = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT, no_wrap=True,
                             overflow=ft.TextOverflow.ELLIPSIS)
        self.on_map = ft.IconButton(ft.Icons.MAP_OUTLINED, tooltip=self.t("show_on_map"), on_click=self._show_on_map,
                                    visible=False)
        self.left = left = ft.Column(
            [
                ft.Row([ft.IconButton(ft.Icons.ADD, tooltip=self.t("new_message"), on_click=self._new,
                                      style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY,
                                                           shape=ft.CircleBorder())),
                        ft.OutlinedButton(self.t("spot_button"), icon=ft.Icons.TERRAIN, on_click=self._spot,
                                          tooltip=self.t("spot_title")),
                        ft.OutlinedButton(self.t("services_button"), icon=ft.Icons.MISCELLANEOUS_SERVICES,
                                          on_click=self._services, tooltip=self.t("services_title")),
                        ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, tooltip=self.t("more"), items=[
                            ft.PopupMenuItem(self.t("mark_all_read"), icon=ft.Icons.MARK_EMAIL_READ,
                                             on_click=self._mark_all_read)])],
                       wrap=True, spacing=6),  # one line: a round + for a new message, Spot, Services, ⋮
                self.conversations,
            ],
            width=None if compact else 330,
            expand=compact,
        )
        self.right = right = ft.Column(
            [
                ft.Row([self.back, ft.Column([self.title, self.where], spacing=0, tight=True, expand=True),
                        self.on_map], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(ft.SelectionArea(self.thread), expand=True, border_radius=8,
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST),
                self.to,
                self.text,
                ft.Row([self.via, ft.IconButton(ft.Icons.MY_LOCATION, tooltip=self.t("pos_insert_mine"),
                                                on_click=self._insert_mine),
                        ft.Container(expand=True), self.count,
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

    MAX_LONG = MAX_MESSAGE_PARTS * (MAX_TEXT - 4)  # up to five messages, each with its " 2/5"

    def _count(self, _e=None) -> None:
        """Characters used of one APRS message; longer text goes as several, the count says how many."""
        text = self.text.value or ""
        if len(text) > self.MAX_LONG:
            self.text.value = text = text[:self.MAX_LONG]
        n = len(message_parts(text))
        if n <= 1:
            self.count.value = f"{len(text)}/{MAX_TEXT}"
            self.count.color = ft.Colors.ON_SURFACE_VARIANT
        else:  # several messages, numbered 1/n … n/n
            self.count.value = self.t("msg_parts", n=n, chars=len(text))
            self.count.color = ft.Colors.PRIMARY
        self.count.weight = ft.FontWeight.BOLD if n > 1 else None
        self.app.page.update()

    # ─── data ─────────────────────────────────────────────────────────────

    def _party(self, m: dict) -> str:
        return (m["from"] if m["direction"] == "in" else m["to"]).upper()

    def _grouped(self) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = {}
        for m in self.engine.messages:
            groups.setdefault(self._party(m), []).append(m)
        return dict(sorted(groups.items(), key=lambda kv: -kv[1][-1]["time"]))

    # ─── unread conversations (kept in a file: a restart or an update keeps them unread) ───

    def _unread_file(self):
        return self.app.folder / "unread.json"

    def _load_unread(self) -> dict[str, int]:
        try:
            data = json.loads(self._unread_file().read_text(encoding="utf-8"))
        except (OSError, ValueError, AttributeError):
            return {}
        if isinstance(data, list):  # the first form: only the callsigns
            return {str(c).upper(): 1 for c in data}
        if isinstance(data, dict):
            return {str(c).upper(): max(1, int(n)) for c, n in data.items() if isinstance(n, int)}
        return {}

    @property
    def unread_total(self) -> int:
        """All unread messages together."""
        return sum(self.unread.values())

    def _save_unread(self) -> None:
        try:
            path = self._unread_file()
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(dict(sorted(self.unread.items()))), encoding="utf-8")
            tmp.replace(path)
        except (OSError, AttributeError):
            pass

    def _set_unread(self, call: str, unread: bool) -> None:
        """One more unread message from the station, or its conversation read."""
        if unread:
            self.unread[call] = self.unread.get(call, 0) + 1
        elif self.unread.pop(call, None) is None:
            return
        self._save_unread()

    def _mark_all_read(self, _e=None) -> None:
        if self.unread:
            self.unread.clear()
            self._save_unread()
        self._signature = None
        self.refresh()
        self.app.page.update()

    # ─── events ───────────────────────────────────────────────────────────

    def on_event(self, kind, data) -> None:
        if kind == "message":
            sender = data["from"].upper()
            if not self._reading(sender):
                self._set_unread(sender, True)

    def _reading(self, call: str) -> bool:
        """The conversation is on screen and somebody looks (not in the background, not minimised)."""
        away = getattr(self.app, "_away", None)
        return self.app.current_key == self.key and self.selected == call and not (away and away())

    def open_conversation(self, call: str) -> None:
        self.selected = call.upper()
        self.to.visible = False
        self._set_unread(self.selected, False)
        self._signature = None
        self.refresh()

    def refresh(self) -> None:
        if self.selected and self._reading(self.selected):
            self._set_unread(self.selected, False)
            self.app.message_read(self.selected)
        groups = self._grouped()
        if getattr(self.engine, "_loaded", False) and self.unread.keys() - groups.keys():  # conversations gone
            self.unread = {c: n for c, n in self.unread.items() if c in groups}
            self._save_unread()
        states = tuple(self.engine.message_state(m.get("msg_no")) for m in self.engine.messages
                       if m["direction"] == "out")
        signature = (len(self.engine.messages), self.selected, states, tuple(sorted(self.unread.items())),
                     self.engine.aprsis is not None, self.engine.config.beacon_is)
        if signature == self._signature:
            return
        self._signature = signature
        self.via.visible = self.engine.aprsis is not None
        if not self.engine.config.message_via:  # not chosen yet: follows the APRS-IS switch in Settings
            via = self._saved_via()
            self.via_radio.selected, self.via_net.selected = via in ("radio", "both"), via in ("internet", "both")
        self.conversations.controls = [self._conversation_tile(call, msgs) for call, msgs in groups.items()]
        if not groups:
            self.conversations.controls = [ft.Text(self.t("no_messages"), color=ft.Colors.ON_SURFACE_VARIANT)]
        self._where()
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
        self.app._update_back()  # the back gesture closes the conversation first

    def can_back(self) -> bool:
        return self.app.compact and bool(self.selected or self.to.visible)

    def go_back(self) -> None:
        self._back(None)

    def _back(self, _e) -> None:
        self.selected = None
        self.to.visible = False
        self._signature = None
        self.refresh()
        self.app.page.update()

    def _conversation_tile(self, call: str, msgs: list[dict]) -> ft.Control:
        last = msgs[-1]
        unread = self.unread.get(call, 0)
        letter = avatar_letter(call)
        return ft.ListTile(
            # a coloured circle with the letter; unread: a red count on it, the callsign and the text in bold
            leading=ft.CircleAvatar(
                content=ft.Text(letter, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                bgcolor=avatar_color(letter), radius=20,
                badge=ft.Badge(label=str(unread) if unread < 100 else "99+", bgcolor=ft.Colors.RED,
                               text_color=ft.Colors.WHITE) if unread else None),
            title=ft.Text(call, weight=ft.FontWeight.BOLD if unread else None, no_wrap=True,
                          overflow=ft.TextOverflow.ELLIPSIS),
            subtitle=ft.Text(last["text"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                             weight=ft.FontWeight.W_600 if unread else None,
                             color=None if unread else ft.Colors.ON_SURFACE_VARIANT),
            trailing=ft.Row([
                ft.Text(clock(last["time"]), size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, tooltip=self.t("more"), items=[
                    ft.PopupMenuItem(self.t("conv_delete"), icon=ft.Icons.DELETE_OUTLINE,
                                     on_click=lambda _e, c=call: self._ask_delete(c))]),
            ], tight=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            selected=call == self.selected,
            on_click=lambda _e, c=call: self.open_conversation(c),
        )

    def _ask_delete(self, call: str) -> None:
        def yes(_e) -> None:
            self.app.page.pop_dialog()
            self.engine.delete_conversation(call)
            self._set_unread(call, False)
            if self.selected == call:
                self.selected = None
            self._signature = None
            self.refresh()
            self.app.page.update()

        self.app.show_dialog(ft.AlertDialog(
            title=ft.Text(self.t("conv_delete_title", call=call)),
            content=ft.Text(self.t("conv_delete_ask")),
            actions=[ft.TextButton(self.t("cancel"), on_click=lambda _e: self.app.page.pop_dialog()),
                     ft.FilledButton(self.t("conv_delete"), icon=ft.Icons.DELETE_OUTLINE, on_click=yes)],
        ))

    def _station(self) -> dict | None:
        heard = self.engine.station.heard
        entry = heard.get(self.selected) if self.selected else None
        return entry if entry and entry.get("latitude") is not None else None

    def _where(self) -> None:
        """The station's distance and direction from us now, and how old its position is."""
        entry = self._station()
        here = self.engine.my_position()
        self.on_map.visible = entry is not None
        self.where.visible = bool(entry and here)
        if entry and here:
            km = distance_km(*here, entry["latitude"], entry["longitude"])
            dist = f"{km * 1000:.0f} m" if km < 1 else f"{km:.1f} km" if km < 10 else f"{km:.0f} km"
            self.where.value = self.t("msg_where", d=dist, dir=bearing(*here, entry["latitude"], entry["longitude"]),
                                      age=self.t.age(time.time() - entry["last_heard"]))

    async def _show_on_map(self, _e) -> None:
        entry = self._station()
        if entry:
            self.app.select("map")
            await self.app.view("map").centre(entry["latitude"], entry["longitude"])

    def _bubble(self, m: dict) -> ft.Control:
        out = m["direction"] == "out"
        meta: list[ft.Control] = [ft.Text(clock(m["time"]), size=11, color=ft.Colors.ON_SURFACE_VARIANT)]
        if m.get("km") is not None:  # how far the sender was when the message came
            km = m["km"]
            dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            dist = f"{km * 1000:.0f} m" if km < 1 else f"{km:.1f} km" if km < 10 else f"{km:.0f} km"
            meta.append(ft.Text(f"📍 {dist} {dirs[round(m.get('bearing', 0) / 45) % 8]}", size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT, tooltip=self.t("msg_distance_then")))
        if m.get("via"):
            meta.append(ft.Text(self.t(f"via_{m['via']}") if m["via"] in ("radio", "internet", "both") else m["via"],
                                size=11, color=ft.Colors.ON_SURFACE_VARIANT))
        if out:
            state = self.engine.message_state(m.get("msg_no"))
            if state in STATE_ICONS:
                icon, color = STATE_ICONS[state]
                meta.append(ft.Icon(icon, size=14, color=color, tooltip=self.t(f"state_{state}")))
        for p in find_positions(m["text"])[:1]:  # a position in the text: see it on the map
            who = m["from"] if not out else m["to"]
            meta.append(ft.IconButton(ft.Icons.MAP_OUTLINED, icon_size=16, tooltip=self.t("pos_on_map"),
                                      style=ft.ButtonStyle(padding=0), width=24, height=24,
                                      on_click=lambda _e, p=p, who=who: self.app.page.run_task(self.app.show_point, *p, who)))
        bubble = ft.Container(
            ft.Column([ft.Text(m["text"], selectable=True),
                       ft.Row(meta, spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)],
                      spacing=2, tight=True),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=12,
            bgcolor=ft.Colors.PRIMARY_CONTAINER if out else ft.Colors.SURFACE_CONTAINER_HIGH,
            # as wide as the text, at most the row: a long message wraps instead of running off the screen
            expand=True, expand_loose=True,
        )
        gap = ft.Container(width=40)  # the other side stays a little free, like in any messenger
        return ft.Row([gap, bubble] if out else [bubble, gap],
                      alignment=ft.MainAxisAlignment.END if out else ft.MainAxisAlignment.START)

    # ─── actions ──────────────────────────────────────────────────────────

    def _insert_mine(self, _e) -> None:
        here = self.engine.my_position()
        if not here:
            self.app.toast(self.t("no_position"), error=True)
            return
        self.insert_text(write_position(*here))

    def insert_text(self, text: str) -> None:
        """Put a text (a position) into the message being written; a new message when no conversation is open."""
        if not self.selected and not self.to.visible:
            self.to.visible = True
            self.to.value = ""
            self._signature = None
            self.refresh()
        old = (self.text.value or "").rstrip()
        self.text.value = f"{old} {text}".strip()
        self._count()

    def _saved_via(self) -> str:
        via = self.engine.config.message_via
        if via in ("radio", "internet", "both"):
            return via
        return "both" if self.engine.config.beacon_is else "radio"

    def _via_value(self) -> str:
        """The way chosen by the two icons; only the radio without APRS-IS."""
        if not self.via.visible:
            return "radio"
        radio, net = self.via_radio.selected, self.via_net.selected
        return "both" if radio and net else "internet" if net else "radio"

    def _flip_via(self, which: str) -> None:
        button, other = (self.via_radio, self.via_net) if which == "radio" else (self.via_net, self.via_radio)
        if button.selected and not other.selected:  # one of them stays on: a message must go somewhere
            self.app.toast(self.t("via_one_needed"))
            return
        button.selected = not button.selected
        self.engine.config.message_via = self._via_value()
        self.app.save_config_soon()  # remembered until changed
        self.app.page.update()

    async def _new(self, _e) -> None:
        # Show the empty form at once (only what changes on screen), then put the cursor in "to"; the list of
        # conversations is rebuilt by the next refresh, unseen. Before, the whole list was rebuilt first and
        # the screen changed only after the keyboard came up: a tap looked missed.
        self.selected = None
        self.to.visible = True
        self.to.value = ""
        self.title.value = self.t("new_message")
        self.thread.controls = []
        self.where.visible = self.on_map.visible = False
        self._sides()
        self.app.page.update()
        await self.to.focus()

    # ─── self-spotting an activation (SOTA, POTA, WWFF, SIOTA) ─────────────

    def _spot(self, _e=None) -> None:
        """A dialog for a self-spot; it goes as an APRS message to the gateway, whose answer then shows in
        that conversation."""
        t = self.t
        try:
            last = json.loads(self.engine.config.spot_last or "{}")
        except ValueError:
            last = {}
        program = ft.Dropdown(label=t("spot_program"), value=last.get("program", "SOTA"), dense=True, width=130,
                              options=[ft.DropdownOption(key=p, text=t("spot_lighthouse") if p == "LH" else p)
                                       for p in PROGRAMS])
        gateway = ft.Dropdown(label=t("spot_gateway"), dense=True, width=180)
        ref = ft.TextField(label=t("spot_ref"), value=last.get("reference", ""), dense=True, width=150,
                           capitalization=ft.TextCapitalization.CHARACTERS)
        freq = ft.TextField(label=t("spot_freq"), value=last.get("frequency", ""), dense=True, width=170,
                            keyboard_type=ft.KeyboardType.NUMBER)
        mode = ft.Dropdown(label=t("spot_mode"), dense=True, width=120)
        comment = ft.TextField(label=t("spot_comment"), value="", dense=True)
        test = ft.Checkbox(label=t("spot_test"), value=False)
        hint = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        error = ft.Text(size=12, color=ft.Colors.ERROR, visible=False)
        preview = ft.Text(size=12, font_family="monospace", selectable=True)

        def current() -> Spot:
            return Spot(program.value or "SOTA", ref.value or "", freq.value or "", mode.value or "",
                        comment.value or "", gateway.value or "", bool(test.value))

        def update_preview() -> None:
            try:
                to, text = build_spot(current(), str(self.engine.me))
                preview.value, error.visible = f"→ {to}: {text}", False
            except SpotError as err:
                preview.value = ""
                error.value, error.visible = t(err.code, example=err.example), bool(ref.value or freq.value)

        def program_changed(_e=None, keep_gateway: str = "") -> None:
            p = program.value or "SOTA"
            choices = gateways_for(p)
            gateway.options = [ft.DropdownOption(key=g, text=GATEWAY_NAMES[g]) for g in choices]
            gateway.value = keep_gateway if keep_gateway in choices else default_gateway(p)
            gateway_changed(keep_mode=mode.value or last.get("mode", "SSB"))

        def gateway_changed(_e=None, keep_mode: str = "") -> None:
            g = gateway.value or "APRS2SOTA"
            mode.options = [ft.DropdownOption(key=m, text=m) for m in MODES[g]]
            wanted = keep_mode or mode.value
            mode.value = wanted if wanted in MODES[g] else "SSB"
            hint.value = t({"APRS2SOTA": "spot_hint_aprs2sota", CAMILLA: "spot_hint_camilla"}.get(g, "spot_hint_apspot"))
            update_preview()
            if _e is not None:
                self.app.page.update()

        program.on_select = lambda e: (program_changed(), self.app.page.update())
        gateway.on_select = gateway_changed
        mode.on_select = lambda _e: (update_preview(), self.app.page.update())
        for field in (ref, freq, comment):
            field.on_change = lambda _e: (update_preview(), self.app.page.update())
        test.on_change = lambda _e: (update_preview(), self.app.page.update())
        program_changed(keep_gateway=last.get("gateway", ""))

        async def send(_e) -> None:
            spot = current()
            try:
                to, text = build_spot(spot, str(self.engine.me))
            except SpotError as err:
                error.value, error.visible = t(err.code, example=err.example), True
                self.app.page.update()
                return
            # by radio over APRS (an iGate in range takes it to the gateway); internet too only when chosen
            via = self._via_value()
            if not await self.app.guard(self.engine.send_aprs_message(to, text, via)):
                return
            self.engine.config.spot_last = json.dumps({
                "program": spot.program, "reference": ref.value or "", "frequency": freq.value or "",
                "mode": mode.value or "", "gateway": gateway.value or ""})
            self.app.save_config_soon()
            self.app.page.pop_dialog()
            self.open_conversation(to)

        self.app.show_dialog(ft.AlertDialog(
            title=ft.Text(t("spot_title")),
            content=ft.Container(ft.Column([
                ft.Row([program, gateway], wrap=True, spacing=8),
                ft.Row([ref, freq, mode], wrap=True, spacing=8),
                comment, test, hint, preview, error,
            ], tight=True, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), width=480),
            scrollable=True,
            actions=[ft.TextButton(t("cancel"), on_click=lambda _e: self.app.page.pop_dialog()),
                     ft.FilledButton(t("spot_send"), icon=ft.Icons.SEND, on_click=send)],
        ))

    # ─── services that answer a message (FIND, REPEAT, WXNOW, UTC, satellites, e-mail) ─────

    def _services(self, _e=None) -> None:
        """A list of the services; a command opens the conversation with it put in the message field,
        ready to send (or to finish: a callsign, an address)."""
        t = self.t

        def use(call: str, command: str):
            async def go(_e) -> None:
                self.app.page.pop_dialog()
                self.compose_to(call)
                self.text.value = command
                self._count()
                await self.text.focus()
            return go

        async def thursday(_e) -> None:
            self.app.page.pop_dialog()
            self.app.select("thursday")

        rows: list[ft.Control] = []
        if self.app.has_view("thursday"):  # first: APRS Thursday, its own screen (once in the menu)
            rows.append(ft.Column([
                ft.Text(self.t("thursday"), weight=ft.FontWeight.BOLD),
                ft.Text(t("svc_thursday"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row([ft.FilledTonalButton(t("svc_thursday_open"), icon=ft.Icons.EVENT, on_click=thursday)]),
            ], tight=True, spacing=4))
        for svc in SERVICES:
            buttons = [ft.OutlinedButton(command.strip() or t("svc_type"), on_click=use(svc.call, command),
                                         style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=10)))
                       for command in svc.commands]
            rows.append(ft.Column([
                ft.Text(svc.call, weight=ft.FontWeight.BOLD, font_family="monospace", selectable=True),
                ft.Text(t(svc.key), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row(buttons, wrap=True, spacing=6, run_spacing=4),
            ], tight=True, spacing=4))
        self.app.show_dialog(ft.AlertDialog(
            title=ft.Text(t("services_title")),
            content=ft.Container(ft.Column([ft.Text(t("services_hint"), size=12), *rows], tight=True, spacing=14),
                                 width=480),
            scrollable=True,
            actions=[ft.TextButton(t("close"), on_click=lambda _e: self.app.page.pop_dialog())],
        ))

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
        via = self._via_value()
        sent = True
        for part in message_parts(text):  # one, or several numbered "1/3", "2/3", "3/3"
            if not await self.app.guard(self.engine.send_aprs_message(to, part, via)):
                sent = False
                break
        if sent:
            self.text.value = ""
            self.count.value, self.count.color = f"0/{MAX_TEXT}", ft.Colors.ON_SURFACE_VARIANT
            self.open_conversation(to)
        await self.text.focus()
