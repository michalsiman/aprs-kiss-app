"""Settings: TNC connection, station, APRS-IS, app."""

from __future__ import annotations

import asyncio
import glob
import os

import flet as ft

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

from ..i18n import LANGUAGES, TEXTS, ssid_labels
from ..symbols import SYMBOLS
from .base import View, short_path

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


def _section(title: str, *controls: ft.Control) -> ft.Control:
    return ft.Card(
        ft.Container(
            ft.Column([ft.Text(title, size=15, weight=ft.FontWeight.BOLD), *controls], spacing=8),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
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

    def build(self) -> ft.Control:
        c = self.engine.config
        t = self.t
        num = ft.NumbersOnlyInputFilter()
        call, _, ssid = c.callsign.partition("-")

        # TNC
        self.connection = ft.Dropdown(label=t("connection"), value=c.connection, width=320,
                                      options=[ft.DropdownOption(key="tcp", text=t("conn_tcp"))]
                                      # phones: no USB serial from Python yet, only KISS over the network
                                      + ([] if self.app.mobile else [ft.DropdownOption(key="serial", text=t("conn_serial"))]),
                                      on_select=lambda _e: self._connection_changed())
        self.host = ft.TextField(label=t("host"), value=c.host, width=240)
        self.port = ft.TextField(label=t("port"), value=str(c.port), width=110, input_filter=num)
        self.device = ft.Dropdown(label=t("device"), value=c.device or None, editable=True, expand=True,
                                  options=self._port_options(c.device))
        self.baudrate = ft.Dropdown(label=t("baudrate"), value=str(c.baudrate), width=150, editable=True,
                                    options=[ft.DropdownOption(key=b, text=b) for b in BAUDRATES])
        self.tcp_row = ft.Row([self.host, self.port], wrap=True)
        self.serial_row = ft.Row([self.device, ft.IconButton(ft.Icons.REFRESH, tooltip=t("refresh_ports"),
                                                             on_click=self._refresh_ports), self.baudrate])
        self.txdelay = ft.TextField(label=t("txdelay"), value=str(c.txdelay_ms or 0), width=320, input_filter=num)

        # Station
        self.call = ft.TextField(label=t("callsign"), value=call, width=160,
                                 capitalization=ft.TextCapitalization.CHARACTERS)
        self.ssid = ft.Dropdown(label=t("ssid"), value=ssid or "0", width=330,
                                options=[ft.DropdownOption(key=str(i), text=label)
                                         for i, label in enumerate(ssid_labels(t.language))])
        self.bbs_ssid = ft.Dropdown(label=t("bbs_ssid"), value=str(c.bbs_ssid), width=200,
                                    options=[ft.DropdownOption(key=str(i), text=str(i)) for i in range(1, 16)])
        self._build_bbs_fields(t)
        self.gps_source = ft.Dropdown(label=t("gps_source"), value=c.gps_source if c.gps_source in ("manual", "usb")
                                      else "manual", width=320, on_select=lambda _e: self._gps_changed(),
                                      options=[ft.DropdownOption(key="manual", text=t("gps_manual")),
                                               ft.DropdownOption(key="usb", text=t("gps_usb"))])
        self.gps_device = ft.Dropdown(label=t("gps_device"), value=c.gps_device or None, editable=True, expand=True,
                                      options=self._port_options(c.gps_device))
        self.gps_baud = ft.Dropdown(label=t("baudrate"), value=str(c.gps_baudrate or 0), width=170,
                                    options=[ft.DropdownOption(key="0", text=t("gps_auto"))] +
                                    [ft.DropdownOption(key=b, text=b) for b in ("4800", "9600", "38400", "115200")])
        self.gps_row = ft.Row([self.gps_device, self.gps_baud,
                               ft.IconButton(ft.Icons.REFRESH, tooltip=t("refresh_ports"),
                                             on_click=lambda _e: self._refresh_gps_ports())])
        self.gps_hint = ft.Text(t("gps_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)
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
        self.beacon = ft.TextField(label=t("beacon"), value=str(c.beacon_minutes or 0), width=420, input_filter=num)
        self.beacon_is = ft.Checkbox(label=t("beacon_is"), value=c.beacon_is)
        self.tracked = ft.TextField(label=t("tracked"), value=c.tracked_callsigns, width=420,
                                    capitalization=ft.TextCapitalization.CHARACTERS)
        self.incoming = ft.Checkbox(label=t("incoming"), value=c.accept_incoming)

        # APRS-IS
        self.aprsis = ft.Checkbox(label=t("aprsis_on"), value=c.aprsis_on, on_change=lambda _e: self._aprsis_changed())
        self.licence = ft.TextField(label=t("licence_ask"), hint_text=t("licence_text"), helper=t("licence_text"))
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
        self.check_updates = ft.Checkbox(label=t("check_updates"), value=c.check_updates)
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
        form = ft.Column(
            [
                self.intro,
                _section(t("tnc_section"), self.connection, self.tcp_row, self.serial_row, self.txdelay),
                _section(t("station"), ft.Row([self.call, self.ssid], wrap=True), self.symbol,
                         ft.Row([self.comment]), self.path,
                         ft.Row([self.lat, self.lon], wrap=True),
                         ft.Text(t("position_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                         self.beacon, self.beacon_is, self.tracked, self.incoming),
                *([] if self.app.mobile else [_section("GPS", self.gps_source, self.gps_row, self.gps_hint)]),
                _section(t("aprsis"), self.aprsis, self.licence, self.is_fields, self.is_state),
                _section("VARA FM", ft.Row([self.vara_host, self.vara_port], wrap=True),
                         ft.Text(t("vara_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT)),
                _section(t("tak"), ft.Row([self.tak_callsign, self.tak_team, self.tak_role], wrap=True),
                         self.tak_interval),
                *([] if self.app.mobile else [_section(t("bbs"), ft.Row([self.bbs_ssid, self.bbs_sessions], wrap=True),
                         ft.Row([self.bbs_idle, self.bbs_tx, self.bbs_max], wrap=True),
                         ft.Text(t("bbs_welcome"), size=12), ft.Row([self.bbs_welcome]),
                         ft.Text(t("bbs_more"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                         ft.Text(short_path(self.engine.bbs_folder()), size=12, font_family="monospace", selectable=True))]),
                _section(t("app_section"), ft.Row([self.language, self.theme], wrap=True), self.check_updates,
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
        return form

    def show_position(self, lat: float, lon: float) -> None:
        self.lat.value, self.lon.value = str(lat), str(lon)

    def _about(self) -> None:
        from ..about import show_about  # noqa: PLC0415

        show_about(self.app)

    def _port_options(self, current: str = "") -> list[ft.DropdownOption]:
        ports = serial_ports()
        options = [ft.DropdownOption(key=d, text=desc) for d, desc in ports]
        if current and not any(d == current for d, _ in ports):
            options.insert(0, ft.DropdownOption(key=current, text=current))
        return options

    def _refresh_ports(self, _e) -> None:
        self.device.options = self._port_options(self.device.value or "")
        if not self.device.options:
            self.app.toast(self.t("no_ports"))

    def _connection_changed(self, update: bool = True) -> None:
        serial = self.connection.value == "serial"
        self.tcp_row.visible = not serial
        self.serial_row.visible = serial

    def _aprsis_changed(self, update: bool = True) -> None:
        on = bool(self.aprsis.value)
        self.licence.visible = on and not self.engine.config.aprsis_on
        self.is_fields.visible = on

    def refresh(self) -> None:
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

    def _gps_changed(self, update: bool = True) -> None:
        usb = self.gps_source.value == "usb"
        self.gps_row.visible = self.gps_hint.visible = usb
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
            "theme": self.theme.value or "auto",
        }
        try:
            for key in ("latitude", "longitude"):
                if data[key]:
                    try:
                        float(data[key])
                    except ValueError:
                        raise ValueError(self.t(key)) from None
            if data["aprsis_enabled"] and not old.aprsis_on:
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
        await asyncio.sleep(0)
