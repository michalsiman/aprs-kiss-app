"""Settings: TNC connection, station, APRS-IS, app."""

from __future__ import annotations

import asyncio
import glob
import logging
import os
from pathlib import Path

import flet as ft

from aprs_kiss_core import android_bt, android_usb, tilemaps, tracker
from aprs_kiss_core.aprsis import licence_confirmed
from aprs_kiss_core.bbs import BbsConfigError
from aprs_kiss_core.bbs.storage import (
    BbsSettings,
    load_settings,
    prepare_folder,
    read_text,
    update_settings,
    write_text,
)
from aprs_kiss_core.config import Config

from .. import distribution, offline_map
from ..i18n import LANGUAGES, TEXTS, ssid_labels
from ..symbols import SYMBOLS
from .base import View, short_path

_LOGGER = logging.getLogger(__name__)

BAUDRATES = ["1200", "4800", "9600", "19200", "38400", "57600", "115200"]


def serial_ports() -> list[tuple[str, str]]:
    """(device, description) of serial ports; on Linux the stable /dev/serial/by-id names first."""
    ports: list[tuple[str, str]] = []
    for path in sorted(glob.glob("/dev/serial/by-id/*")):
        ports.append((path, f"{os.path.basename(path)} → {os.path.realpath(path)}"))
    try:
        from serial.tools import list_ports  # noqa: PLC0415

        for p in list_ports.comports():
            if not any(os.path.realpath(d) == p.device for d, _ in ports):
                # Windows repeats the port in the description: "USB-SERIAL CH340 (COM5)"
                desc = (p.description or "").replace(f"({p.device})", "").strip()
                ports.append((p.device, f"{p.device} – {desc}" if desc and desc != "n/a" else p.device))
    except ImportError:
        pass
    return ports


TEXT = 14


def _section(title: str, icon: str, *controls: ft.Control, expanded: bool = False) -> ft.Control:
    """One block of settings, folded up: a tap on its title opens it (the values stay while it is closed)."""
    shape = ft.RoundedRectangleBorder(radius=12)
    return ft.Card(
        ft.ExpansionTile(
            title=ft.Text(title, size=15, weight=ft.FontWeight.BOLD),
            leading=ft.Icon(icon, color=ft.Colors.PRIMARY),
            controls=[ft.Container(ft.Column(list(controls), spacing=8),
                                   # top: room for the first field's label, which sits on the field's edge
                                   padding=ft.Padding.only(left=14, right=14, top=8, bottom=12))],
            expanded=expanded, maintain_state=True, shape=shape, collapsed_shape=shape,
            expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def _compact(control: ft.Control) -> None:
    """Smaller text and input boxes than the Material defaults, all through the settings form."""
    if isinstance(control, (ft.TextField, ft.Dropdown)):
        control.dense = True
        control.text_size = TEXT
        control.label_style = ft.TextStyle(size=TEXT)
        vertical = 4 if isinstance(control, ft.Dropdown) else 10
        control.content_padding = ft.Padding.symmetric(horizontal=10, vertical=vertical)
    elif isinstance(control, ft.Checkbox):
        control.label_style = ft.TextStyle(size=TEXT)
        control.visual_density = ft.VisualDensity.COMPACT
    elif isinstance(control, ft.Text) and control.size is None:
        control.size = TEXT
    for attr in ("content", "controls"):
        child = getattr(control, attr, None)
        for c in child if isinstance(child, list) else [child]:
            if isinstance(c, ft.Control):
                _compact(c)


class SettingsView(View):
    key = "settings"
    lazy = True
    icon = ft.Icons.SETTINGS_OUTLINED
    selected_icon = ft.Icons.SETTINGS

    @property
    def usb_ok(self) -> bool:
        """The USB (OTG) connection exists: in the Android app (APRS_KISS_USB=1 shows it for tests)."""
        return android_usb.available() or os.environ.get("APRS_KISS_USB") == "1"

    def build(self) -> ft.Control:
        c = self.engine.config
        t = self.t
        num = ft.NumbersOnlyInputFilter()
        call, _, ssid = c.callsign.partition("-")

        # TNC
        self.connection = ft.Dropdown(label=t("connection"), value=c.connection, width=320,
                                      options=[ft.DropdownOption(key="tcp", text=t("conn_tcp"))]
                                      # Android: a TNC on the phone's USB port (OTG); computers: a serial port
                                      + ([ft.DropdownOption(key="usb", text=t("conn_usb")),
                                          ft.DropdownOption(key="bt", text=t("conn_bt"))] if self.usb_ok
                                         else [] if self.app.mobile
                                         else [ft.DropdownOption(key="serial", text=t("conn_serial"))]),
                                      on_select=lambda _e: self._connection_changed())
        self.host = ft.TextField(label=t("host"), value=c.host, width=240)
        self.port = ft.TextField(label=t("port"), value=str(c.port), width=110, input_filter=num)
        self.device = ft.Dropdown(label=t("device"), value=c.device or None, editable=True, expand=True,
                                  options=self._port_options(c.device))
        self.baudrate = ft.Dropdown(label=t("baudrate"), value=str(c.baudrate), width=120 if self.app.compact else 150,
                                    editable=True,
                                    options=[ft.DropdownOption(key=b, text=b) for b in BAUDRATES])
        self.tcp_row = ft.Row([self.host, self.port], wrap=True)
        self.serial_row = ft.Row([self.device, ft.IconButton(ft.Icons.REFRESH, tooltip=t("refresh_ports"),
                                                             on_click=self._refresh_ports), self.baudrate])
        self.txdelay = ft.TextField(label=t("txdelay"), value=str(c.txdelay_ms or 0), width=320, input_filter=num)

        # Station
        self.call = ft.TextField(label=t("callsign"), value=call, width=160,
                                 capitalization=ft.TextCapitalization.CHARACTERS,
                                 autofocus=not c.configured, on_change=lambda _e: self._mark_call())
        self.ssid = ft.Dropdown(label=t("ssid"), value=ssid or "0", width=330,
                                options=[ft.DropdownOption(key=str(i), text=label)
                                         for i, label in enumerate(ssid_labels(t.language))])
        self.bbs_ssid = ft.Dropdown(label=t("bbs_ssid"), value=str(c.bbs_ssid), width=200,
                                    options=[ft.DropdownOption(key=str(i), text=str(i)) for i in range(1, 16)])
        self._build_bbs_fields(t)
        # a phone: its own GPS; a computer: a USB GPS module
        sources = ("manual", "phone") if self.app.mobile else ("manual", "usb")
        self.gps_source = ft.Dropdown(label=t("gps_source"), value=c.gps_source if c.gps_source in sources
                                      else "manual", width=320, on_select=lambda _e: self._gps_changed(),
                                      options=[ft.DropdownOption(key=k, text=t(f"gps_{k}").split(" (")[0] if self.app.compact
                                                                   else t(f"gps_{k}")) for k in sources])
        self.gps_device = ft.Dropdown(label=t("gps_device"), value=c.gps_device or None, editable=True, expand=True,
                                      options=self._port_options(c.gps_device))
        self.gps_baud = ft.Dropdown(label=t("baudrate"), value=str(c.gps_baudrate or 0), width=170,
                                    options=[ft.DropdownOption(key="0", text=t("gps_auto"))] +
                                    [ft.DropdownOption(key=b, text=b) for b in ("4800", "9600", "38400", "115200")])
        self.gps_row = ft.Row([self.gps_device, self.gps_baud,
                               ft.IconButton(ft.Icons.REFRESH, tooltip=t("refresh_ports"),
                                             on_click=lambda _e: self._refresh_gps_ports())])
        self.gps_hint = ft.Text(t("gps_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.gps_phone_hint = ft.Text(t("gps_phone_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._gps_changed(update=False)
        self.vara_host = ft.TextField(label=t("vara_host"), value=c.vara_host, width=260, hint_text="127.0.0.1")
        self.vara_port = ft.TextField(label=t("vara_port"), value=str(c.vara_port or 8300), width=260,
                                      keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.NumbersOnlyInputFilter())
        from aprs_kiss_core import tak  # noqa: PLC0415
        self.tak_callsign = ft.TextField(label=t("tak_callsign"), value=c.tak_callsign, width=330,
                                         capitalization=ft.TextCapitalization.CHARACTERS)
        self.tak_team = ft.Dropdown(label=t("tak_team"), value=c.tak_team if c.tak_team in tak.TEAMS else "Cyan",
                                    width=200, options=[ft.DropdownOption(key=x, text=x) for x in tak.TEAMS])
        self.tak_role = ft.Dropdown(label=t("tak_role"), value=c.tak_role if c.tak_role in tak.ROLES else "Team Member",
                                    width=220, options=[ft.DropdownOption(key=x, text=x) for x in tak.ROLES])
        self.tak_interval = ft.TextField(label=t("tak_interval"), value=str(c.tak_interval_min), width=440,
                                         keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.NumbersOnlyInputFilter())
        lang_index = 3 if t.language == "cs" else 2
        symbols = [ft.DropdownOption(key=s[0], text=f"{s[1]}  {s[lang_index]} ({s[0]})") for s in SYMBOLS]
        if not any(s[0] == c.symbol for s in SYMBOLS):
            symbols.insert(0, ft.DropdownOption(key=c.symbol, text=c.symbol))
        self.symbol = ft.Dropdown(label=t("symbol"), value=c.symbol, width=330, options=symbols)
        self.comment = ft.TextField(label=t("comment"), value=c.comment, expand=True, max_length=43)
        self.path = ft.TextField(label=t("digipath"), value=c.path, width=240,
                                 capitalization=ft.TextCapitalization.CHARACTERS)
        self.lat = ft.TextField(label=t("latitude"), value="" if c.latitude is None else str(c.latitude), width=160)
        self.lon = ft.TextField(label=t("longitude"), value="" if c.longitude is None else str(c.longitude), width=160)
        # with a GPS chosen: where it says we are, under the (then unused) typed-in fields
        self.gps_now = ft.Text(size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY, visible=False)
        self._gps_changed(update=False)
        self.beacon = ft.TextField(label=t("beacon"), value=str(c.beacon_minutes or 0), width=420, input_filter=num)
        self.beacon_is = ft.Checkbox(label=t("beacon_is"), value=c.beacon_is)
        self.tracked = ft.TextField(label=t("tracked"), value=c.tracked_callsigns, width=420,
                                    capitalization=ft.TextCapitalization.CHARACTERS)
        self.incoming = ft.Checkbox(label=t("incoming"), value=c.accept_incoming)

        # APRS-IS
        self.aprsis = ft.Checkbox(label=t("aprsis_on"), value=c.aprsis_enabled, on_change=lambda _e: self._aprsis_changed())
        self.licence = ft.TextField(hint_text=t("licence_text"), helper=t("licence_text"), width=420)
        self.licence_box = ft.Column([ft.Text(t("licence_ask"), size=13, color=ft.Colors.PRIMARY), self.licence],
                                     spacing=4)
        self.is_host = ft.TextField(label=t("server"), value=c.aprsis_host, width=240)
        self.is_port = ft.TextField(label=t("port"), value=str(c.aprsis_port), width=110, input_filter=num)
        self.passcode = ft.TextField(label=t("passcode"), value=c.aprsis_passcode, width=240, password=True,
                                     can_reveal_password=True, helper=t("pass_hint"), input_filter=num)
        self.radius = ft.TextField(label=t("radius"), value=str(c.aprsis_radius_km), width=420, input_filter=num)
        self.igate_rx = ft.Checkbox(label=t("igate_rx"), value=c.igate_rx)
        self.igate_tx = ft.Checkbox(label=t("igate_tx"), value=c.igate_tx)
        self.is_state = ft.Text(color=ft.Colors.ON_SURFACE_VARIANT)
        self.is_fields = ft.Column([ft.Row([self.is_host, self.is_port], wrap=True), self.passcode, self.radius,
                                    self.igate_rx, self.igate_tx], spacing=12)

        # App
        # APRS digipeater
        mins = lambda values: [ft.DropdownOption(key=str(n), text=f"{n} min") for n in values]  # noqa: E731
        self.trk_mode = ft.Dropdown(label=t("trk_mode"), value=c.tracker_mode, width=420,
                                    on_select=lambda _e: self._trk_changed(),
                                    options=[ft.DropdownOption(key="fixed", text=t("trk_fixed")),
                                             ft.DropdownOption(key="smart", text=t("trk_smart"))])
        self.trk_minutes = ft.Dropdown(label=t("trk_minutes"), value=str(c.tracker_minutes), width=200,
                                       options=mins(sorted({*tracker.FIXED_MINUTES, c.tracker_minutes})))
        self.trk_profile = ft.Dropdown(label=t("trk_profile"), value=c.tracker_profile, width=200,
                                       options=[ft.DropdownOption(key=k, text=t(f"trk_{k}")) for k in ("walk", "bike", "car")])
        self.trk_still = ft.Dropdown(label=t("trk_still"), value=str(c.tracker_still_minutes), width=200,
                                     options=mins(sorted({*tracker.STILL_MINUTES, c.tracker_still_minutes})))
        self.trk_hint = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._trk_changed(update=False)
        self.digi_mode = ft.Dropdown(label=t("digi_mode"), value=c.digi_mode if c.digi_mode in ("off", "fillin", "wide")
                                     else "off", width=340, on_select=lambda _e: self._digi_changed(),
                                     options=[ft.DropdownOption(key=k, text=t(f"digi_{k}")) for k in ("off", "fillin", "wide")])
        self.digi_hops = ft.Dropdown(label=t("digi_hops"), value=str(c.digi_max_hops or 2), width=200,
                                     options=[ft.DropdownOption(key=str(n), text=str(n)) for n in (1, 2, 3)])
        self.digi_aliases = ft.TextField(label=t("digi_aliases"), value=c.digi_aliases, width=340, hint_text="RELAY",
                                         capitalization=ft.TextCapitalization.CHARACTERS)
        self.digi_hint = ft.Text(t("digi_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._digi_changed(update=False)
        # running in the background (Android) and keeping the screen on
        self.run_bg = ft.Checkbox(label=t("run_background"), value=c.run_background)
        self.keep_screen = ft.Dropdown(label=t("keep_screen"), value=c.keep_screen_on if c.keep_screen_on in (
            "never", "tak", "always") else "never", width=320,
            options=[ft.DropdownOption(key=k, text=t(f"keep_{k}")) for k in ("never", "tak", "always")])
        self.sound_boxes = {key: ft.Checkbox(label=t(key), value=getattr(c, key))
                            for key in ("sound_tx", "sound_messages", "sound_chat", "sound_tak")}
        self.check_updates = ft.Checkbox(label=t("check_updates"), value=c.check_updates,
                                         visible=not distribution.store_updates())  # Google Play updates it
        self.theme = ft.Dropdown(label=t("theme"), value=c.theme if c.theme in ("auto", "light", "dark") else "auto",
                                 width=240,
                                 options=[ft.DropdownOption(key="auto", text=t("theme_auto")),
                                          ft.DropdownOption(key="light", text=t("theme_light")),
                                          ft.DropdownOption(key="dark", text=t("theme_dark"))],
                                 on_select=lambda e: self.app.set_theme(e.control.value or "auto"))
        self.language = ft.Dropdown(label=t("language"), value=c.language or "", width=240,
                                    options=[ft.DropdownOption(key="", text=t("lang_auto")),
                                             *[ft.DropdownOption(key=code, text=name)
                                               for code, name in LANGUAGES.items()]])

        self.error = ft.Text(color=ft.Colors.ERROR)
        self.intro = ft.Text(t("first_run"), color=ft.Colors.PRIMARY, visible=not c.configured)
        self._connection_changed(update=False)
        self._aprsis_changed(update=False)
        first = not c.configured  # the very first time: the blocks that must be filled in are open
        form = ft.Column(
            [
                self.intro,
                _section(t("tnc_section"), ft.Icons.CABLE, self.connection, self.tcp_row, self.serial_row, self.txdelay, expanded=first),
                station := _section(t("station"), ft.Icons.PERSON_PIN_CIRCLE, ft.Row([self.call, self.ssid], wrap=True), self.symbol,
                         ft.Row([self.comment]), self.path,
                         ft.Row([self.lat, self.lon], wrap=True), self.gps_now,
                         ft.Text(t("position_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                         self.beacon, self.beacon_is, self.tracked, self.incoming, expanded=first),
                _section("GPS", ft.Icons.GPS_FIXED, self.gps_source, self.gps_phone_hint) if self.app.mobile else
                _section("GPS", ft.Icons.GPS_FIXED, self.gps_source, self.gps_row, self.gps_hint),
                _section(t("trk_section"), ft.Icons.ROUTE, self.trk_mode,
                         ft.Row([self.trk_minutes, self.trk_profile, self.trk_still], wrap=True), self.trk_hint),
                _section(t("digi"), ft.Icons.REPEAT, self.digi_mode, self.digi_hops, self.digi_aliases, self.digi_hint),
                _section(t("aprsis"), ft.Icons.PUBLIC, self.aprsis, self.licence_box, self.is_fields, self.is_state),
                _section("VARA FM", ft.Icons.SETTINGS_INPUT_ANTENNA, ft.Row([self.vara_host, self.vara_port], wrap=True),
                         ft.Text(t("vara_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)),
                _section(t("tak"), ft.Icons.RADAR, ft.Row([self.tak_callsign, self.tak_team, self.tak_role], wrap=True),
                         self.tak_interval),
                *([] if self.app.mobile else [_section(t("bbs"), ft.Icons.DNS, ft.Row([self.bbs_ssid, self.bbs_sessions], wrap=True),
                         ft.Row([self.bbs_idle, self.bbs_tx, self.bbs_max], wrap=True),
                         ft.Text(t("bbs_welcome"), size=12), ft.Row([self.bbs_welcome]),
                         ft.Text(t("bbs_more"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                         ft.Text(short_path(self.engine.bbs_folder()), size=12, font_family="monospace", selectable=True))]),
                self._maps_section(),
                _section(t("bg_section"), ft.Icons.PHONELINK_LOCK,
                         *([self.run_bg, ft.Text(t("bg_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)]
                           if self.app.mobile else []),
                         self.keep_screen),
                _section(t("sounds"), ft.Icons.VOLUME_UP, *self.sound_boxes.values(),
                         ft.Row([ft.OutlinedButton(t("sound_test"), icon=ft.Icons.PLAY_ARROW,
                                                   on_click=self._test_sounds)])),
                _section(t("app_section"), ft.Icons.TUNE, ft.Row([self.language, self.theme], wrap=True),
                         self.check_updates,
                         ft.Row([ft.OutlinedButton(t("about"), icon=ft.Icons.INFO_OUTLINE,
                                                   on_click=lambda _e: self._about())])),
                self.error,
                ft.Row([ft.FilledButton(t("save"), icon=ft.Icons.SAVE, on_click=self._save)]),
                ft.Container(height=24),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            expand=True,
            spacing=8,
        )
        _compact(form)
        self.station_tile = station.content
        self._mark_call()
        return form

    def _mark_call(self) -> None:
        """Without a callsign nothing works: the field is framed red until there is one (and it is saved)."""
        missing = not (self.call.value or "").strip() or not self.engine.config.configured
        empty = not (self.call.value or "").strip()
        self.call.border_color = ft.Colors.ERROR if missing else None
        self.call.focused_border_color = ft.Colors.ERROR if missing else None
        self.call.error = "!" if empty else None  # short: the field is narrow, the message says the rest
        try:
            self.call.update()
        except RuntimeError:  # not on the screen yet: drawn with the rest
            pass

    async def require_call(self) -> None:
        """Someone wants to leave Settings with no callsign saved: back to its field."""
        self.station_tile.expanded = True
        self._mark_call()
        self.app.page.update()
        try:
            await self.call.focus()
        except RuntimeError:
            pass

    async def _test_sounds(self, _e) -> None:
        """Each sound once, so they can be heard before choosing."""
        for kind in ("tx", "message", "chat", "tak"):
            self.app.sounds.play(kind, force=True)
            await asyncio.sleep(0.8)

    def show_position(self, lat: float, lon: float) -> None:
        self.lat.value, self.lon.value = str(lat), str(lon)

    def _about(self) -> None:
        from ..about import show_about  # noqa: PLC0415

        show_about(self.app)

    def _port_options(self, current: str = "") -> list[ft.DropdownOption]:
        kind = self.connection.value if hasattr(self, "connection") else self.engine.config.connection
        if kind == "bt":  # the paired Bluetooth devices
            ports = [(d, d) for d in android_bt.list_devices()]
        else:
            ports = [(d, d) for d in android_usb.list_devices()] if self.usb_ok else serial_ports()
        options = [ft.DropdownOption(key=d, text=desc) for d, desc in ports]
        if current and not any(d == current for d, _ in ports):
            options.insert(0, ft.DropdownOption(key=current, text=current))
        return options

    def _refresh_ports(self, _e) -> None:
        self.device.options = self._port_options(self.device.value or "")
        if not self.device.options:
            self.app.toast(self.t("bt_none" if self.connection.value == "bt" else "no_ports"))

    def _connection_changed(self, update: bool = True) -> None:
        serial = self.connection.value in ("serial", "usb", "bt")
        self.tcp_row.visible = not serial
        self.serial_row.visible = serial
        self.baudrate.visible = self.connection.value != "bt"  # a Bluetooth link has no line speed
        self.device.label = self.t("bt_device") if self.connection.value == "bt" else self.t("device")
        if update:
            self.device.options = self._port_options(self.device.value or "")
            if self.connection.value == "bt" and not self.device.options:
                self.app.toast(self.t("bt_none"))
            self.app.page.update()

    def _digi_changed(self, update: bool = True) -> None:
        self.digi_hops.visible = self.digi_mode.value == "wide"  # WIDE1-1 is always one hop
        if update:
            self.app.page.update()

    def _aprsis_changed(self, update: bool = True) -> None:
        on = bool(self.aprsis.value)
        # typed once is enough; the box, not the field, is shown and hidden: a text field that starts
        # hidden does not appear when made visible later (Flet), so the sentence could not be typed
        self.licence_box.visible = on and not self.engine.config.licence_confirmed
        self.is_fields.visible = on

    def _show_gps_now(self) -> None:
        if not self.gps_now.visible:
            return
        source = self.t("gps_phone") if self.gps_source.value == "phone" else self.t("gps_usb")
        fix = self.engine.gps_fix()
        if fix and self.gps_source.value == self.engine.config.gps_source:
            accuracy = f" (±{fix.accuracy_m:.0f} m)" if fix.accuracy_m else ""
            self.gps_now.value = f"{source}: {fix.latitude:.5f}, {fix.longitude:.5f}{accuracy}"
        else:
            self.gps_now.value = f"{source}: {self.t('gps_nofix')}"

    def refresh(self) -> None:
        self._show_gps_now()
        s = self.engine.status().get("aprsis")
        if not s:
            self.is_state.value = ""
            return
        if s["verified"]:
            state = f"{self.t('verified')} ({s['server'] or ''})"
        elif s["connected"]:
            state = self.t("unverified")
        else:
            state = self.t("disconnected") + (f" – {s['error']}" if s.get("error") else "")
        self.is_state.value = f"{self.t('aprsis_state')}: {state}"

    def _trk_changed(self, update: bool = True) -> None:
        smart = self.trk_mode.value == "smart"
        self.trk_minutes.visible = not smart
        self.trk_profile.visible = self.trk_still.visible = smart
        self.trk_hint.value = self.t("trk_hint_smart" if smart else "trk_hint_fixed")
        if update:
            self.app.page.update()

    # ─── imported offline maps: take effect at once, no Save needed ─────

    def _maps_section(self) -> ft.Control:
        t = self.t
        self.maps_list = ft.Column(spacing=0)
        self.maps_busy = ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2), ft.Text(t("maps_importing"))],
                                visible=False)
        self._list_maps()
        return _section(t("maps_section"), ft.Icons.TERRAIN,
                        ft.Text(t("maps_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        self.maps_list, self.maps_busy,
                        ft.Row([ft.OutlinedButton(t("maps_import"), icon=ft.Icons.FILE_OPEN, on_click=self._import_maps)],
                               wrap=True))

    def _list_maps(self) -> None:
        opened = {str(source.path): source for _, source in offline_map.custom_maps()}
        rows = []
        for path in self.engine.config.map_paths:
            source = opened.get(path)
            text = source.describe() if source else f"{Path(path).name} – {self.t('maps_broken')}"
            rows.append(ft.Row([
                ft.Icon(ft.Icons.TERRAIN if source else ft.Icons.ERROR_OUTLINE, size=18,
                        color=ft.Colors.PRIMARY if source else ft.Colors.ERROR),
                ft.Text(text, size=13, expand=True, tooltip=path),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip=self.t("maps_remove"),
                              on_click=lambda _e, p=path: self.app.page.run_task(self._remove_map, p)),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER))
        self.maps_list.controls = rows or [ft.Text(self.t("maps_none"), size=13, italic=True)]

    async def _import_maps(self, _e) -> None:
        try:
            files = await ft.FilePicker().pick_files(dialog_title=self.t("maps_import"), allow_multiple=True)
        except Exception as err:  # noqa: BLE001 - the picker is not there (some web setups)
            _LOGGER.warning("File picker failed: %s", err)
            files = None
        if not files:
            return
        if not any(f.path for f in files):
            self.app.toast(self.t("maps_web"))
            return
        self.maps_busy.visible = True
        self.app.page.update()
        added, errors = [], []
        folder = self.app.folder / "maps"
        for f in files:
            if not f.path:
                continue
            try:
                found = await asyncio.to_thread(tilemaps.import_file, f.path, folder, not self.app.mobile)
                added += [str(p) for p in found]
            except tilemaps.MapError as err:
                _LOGGER.warning("Map %s not imported: %s", f.name, err)
                errors.append(f"{f.name}: {self.t('map_err_' + err.code)}")
            except OSError as err:
                errors.append(f"{f.name}: {err}")
        paths = self.engine.config.map_paths
        paths += [p for p in added if p not in paths]
        if added:
            await self.app.set_map_files(paths)
        self.maps_busy.visible = False
        self._list_maps()
        if errors:
            self.app.toast("\n".join(errors), seconds=12)
        elif added:
            self.app.toast(self.t("maps_added"), seconds=8)
        self.app.page.update()

    async def _remove_map(self, path: str) -> None:
        paths = [p for p in self.engine.config.map_paths if p != path]
        await self.app.set_map_files(paths)
        await asyncio.to_thread(tilemaps.remove_map, path, self.app.folder / "maps")
        self._list_maps()
        self.app.page.update()

    def _gps_changed(self, update: bool = True) -> None:
        usb = self.gps_source.value == "usb"
        self.gps_row.visible = self.gps_hint.visible = usb
        self.gps_phone_hint.visible = self.gps_source.value == "phone"
        if not hasattr(self, "gps_now"):
            return  # still building the form: called again once the position fields exist
        gps = self.gps_source.value in ("phone", "usb")
        self.lat.disabled = self.lon.disabled = gps
        self.lat.hint_text = self.lon.hint_text = "GPS" if gps else None
        self.gps_now.visible = gps
        self._show_gps_now()
        if update:
            self.app.page.update()

    def _refresh_gps_ports(self) -> None:
        self.gps_device.options = self._port_options(self.gps_device.value)
        self.app.page.update()

    # ─── BBS SERVER: these fields live in the BBS folder (bbs.toml, welcome.txt), not in the app's config

    def _build_bbs_fields(self, t) -> None:
        folder = self.engine.bbs_folder()
        try:
            prepare_folder(folder, t.language)
            st = load_settings(folder)
        except (BbsConfigError, OSError):
            st = BbsSettings()
        number = dict(width=200, keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.NumbersOnlyInputFilter())
        self.bbs_sessions = ft.TextField(label=t("bbs_max_sessions"), value=str(st.max_sessions), **number)
        self.bbs_idle = ft.TextField(label=t("bbs_idle_sec"), value=str(st.idle_timeout_sec), **{**number, "width": 260})
        self.bbs_tx = ft.TextField(label=t("bbs_max_tx"), value=str(st.max_tx_min), **{**number, "width": 420})
        self.bbs_max = ft.TextField(label=t("bbs_max_messages"), value=str(st.max_messages), **{**number, "width": 320})
        self.bbs_welcome = ft.TextField(value=read_text(folder, "welcome.txt").rstrip("\n"), expand=True,
                                        multiline=True, min_lines=5, max_lines=14,
                                        text_style=ft.TextStyle(font_family="monospace"))

    def _save_bbs(self) -> None:
        def number(field: ft.TextField, low: int) -> int:
            try:
                value = int((field.value or "").strip())
            except ValueError:
                raise ValueError(field.label) from None
            if value < low:
                raise ValueError(f"{field.label} >= {low}")
            return value

        values = {("limits", "max_sessions"): number(self.bbs_sessions, 1),
                  ("limits", "idle_timeout_sec"): number(self.bbs_idle, 10),
                  ("limits", "max_tx_min"): number(self.bbs_tx, 0),
                  ("limits", "max_messages"): number(self.bbs_max, 0)}
        folder = self.engine.bbs_folder()
        prepare_folder(folder, self.t.language)
        update_settings(folder, values)
        write_text(folder, "welcome.txt", self.bbs_welcome.value or "")

    async def _save(self, _e) -> None:
        old = self.engine.config
        call = (self.call.value or "").strip().upper()
        ssid = self.ssid.value or "0"
        data = {
            **old.to_dict(),
            "connection": self.connection.value, "host": (self.host.value or "").strip(), "port": self.port.value,
            "device": (self.device.value or "").strip(), "baudrate": self.baudrate.value,
            "txdelay_ms": self.txdelay.value,
            "callsign": f"{call}-{ssid}" if call and ssid != "0" else call,
            "symbol": self.symbol.value, "comment": self.comment.value, "path": self.path.value,
            "latitude": (self.lat.value or "").replace(",", ".").strip(),
            "longitude": (self.lon.value or "").replace(",", ".").strip(),
            "beacon_minutes": self.beacon.value, "beacon_is": self.beacon_is.value,
            "tracked_callsigns": self.tracked.value, "accept_incoming": self.incoming.value,
            "bbs_ssid": self.bbs_ssid.value or "1",
            "gps_source": self.gps_source.value or "manual", "gps_device": (self.gps_device.value or "").strip(),
            "gps_baudrate": self.gps_baud.value or "0",
            "vara_host": (self.vara_host.value or "").strip(), "vara_port": self.vara_port.value or "8300",
            "tak_callsign": (self.tak_callsign.value or "").strip().upper(), "tak_team": self.tak_team.value or "Cyan",
            "tak_role": self.tak_role.value or "Team Member", "tak_interval_min": self.tak_interval.value or "0",
            "aprsis_enabled": self.aprsis.value, "aprsis_host": self.is_host.value, "aprsis_port": self.is_port.value,
            "aprsis_passcode": self.passcode.value, "aprsis_radius_km": self.radius.value,
            "igate_rx": self.igate_rx.value, "igate_tx": self.igate_tx.value,
            "language": self.language.value or "",
            "check_updates": self.check_updates.value,
            **{key: box.value for key, box in self.sound_boxes.items()},
            "tracker_mode": self.trk_mode.value or "fixed", "tracker_minutes": self.trk_minutes.value or "2",
            "tracker_profile": self.trk_profile.value or "car", "tracker_still_minutes": self.trk_still.value or "60",
            "digi_mode": self.digi_mode.value or "off", "digi_max_hops": self.digi_hops.value or "2",
            "digi_aliases": (self.digi_aliases.value or "").strip().upper(),
            "run_background": bool(self.run_bg.value), "keep_screen_on": self.keep_screen.value or "never",
            "theme": self.theme.value or "auto",
        }
        try:
            for key in ("latitude", "longitude"):
                if data[key]:
                    try:
                        float(data[key])
                    except ValueError:
                        raise ValueError(self.t(key)) from None
            if data["aprsis_enabled"] and not old.licence_confirmed:
                # Switching APRS-IS on needs the licence statement typed out.
                statements = [texts["licence_text"] for texts in TEXTS.values() if "licence_text" in texts]
                if not licence_confirmed(self.licence.value, statements):
                    raise ValueError(self.t("licence_required"))
                data["licence_confirmed"] = True
            conf = Config.from_dict(data).validate()
        except ValueError as err:
            self.error.value = f"{self.t('invalid')}: {err}"
            return
        self.error.value = ""
        if not call:  # the one thing that is needed
            self.error.value = self.t("call_required")
            await self.require_call()
            return
        if data["gps_source"] == "usb" and not data["gps_device"]:
            self.error.value = f"{self.t('invalid')}: {self.t('gps_device')}"
            return
        if (data["gps_source"] == "usb" and data["connection"] == "serial"
                and data["gps_device"] == data["device"]):
            self.error.value = f"{self.t('invalid')}: {self.t('gps_same_port')}"
            return
        try:
            await asyncio.to_thread(self._save_bbs)
        except (BbsConfigError, OSError, ValueError) as err:
            self.error.value = f"{self.t('invalid')}: {err}"
            return
        await self.app.apply_config(conf)
        self._mark_call()
        self._aprsis_changed()  # the licence sentence, once typed, goes away
        await asyncio.sleep(0)
