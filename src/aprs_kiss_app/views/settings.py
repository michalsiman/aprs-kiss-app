"""Settings: TNC connection, station, APRS-IS, app."""

from __future__ import annotations

import asyncio
import glob
import os

import flet as ft

from aprs_kiss_core.aprsis import licence_confirmed
from aprs_kiss_core.config import Config

from ..symbols import SSIDS, SYMBOLS
from .base import View

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
                ports.append((p.device, f"{p.device} – {p.description}"))
    except ImportError:
        pass
    return ports


def _section(title: str, *controls: ft.Control) -> ft.Control:
    return ft.Card(
        ft.Container(
            ft.Column([ft.Text(title, size=16, weight=ft.FontWeight.BOLD), *controls], spacing=12),
            padding=ft.Padding.all(16),
        ),
    )


class SettingsView(View):
    key = "settings"
    icon = ft.Icons.SETTINGS_OUTLINED
    selected_icon = ft.Icons.SETTINGS

    def build(self) -> ft.Control:
        c = self.engine.config
        t = self.t
        num = ft.NumbersOnlyInputFilter()
        call, _, ssid = c.callsign.partition("-")

        # TNC
        self.connection = ft.Dropdown(label=t("connection"), value=c.connection, width=320,
                                      options=[ft.DropdownOption(key="tcp", text=t("conn_tcp")),
                                               ft.DropdownOption(key="serial", text=t("conn_serial"))],
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
                                         for i, label in enumerate(SSIDS[t.language])])
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
        self.tracked = ft.TextField(label=t("tracked"), value=c.tracked_callsigns,
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
        self.language = ft.Dropdown(label=t("language"), value=c.language or "", width=240,
                                    options=[ft.DropdownOption(key="", text=t("lang_auto")),
                                             ft.DropdownOption(key="cs", text="Čeština"),
                                             ft.DropdownOption(key="en", text="English")])

        self.error = ft.Text(color=ft.Colors.ERROR)
        self.intro = ft.Text(t("first_run"), color=ft.Colors.PRIMARY, visible=not c.configured)
        self._connection_changed(update=False)
        self._aprsis_changed(update=False)
        return ft.Column(
            [
                self.intro,
                _section(t("tnc_section"), self.connection, self.tcp_row, self.serial_row, self.txdelay),
                _section(t("station"), ft.Row([self.call, self.ssid], wrap=True), self.symbol,
                         ft.Row([self.comment]), self.path,
                         ft.Row([self.lat, self.lon], wrap=True),
                         ft.Text(t("position_hint"), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                         self.beacon, self.beacon_is, self.tracked, self.incoming),
                _section(t("aprsis"), self.aprsis, self.licence, self.is_fields, self.is_state),
                _section(t("app_section"), self.language, self.check_updates,
                         ft.Row([ft.OutlinedButton(t("about"), icon=ft.Icons.INFO_OUTLINE,
                                                   on_click=lambda _e: self._about())])),
                self.error,
                ft.Row([ft.FilledButton(t("save"), icon=ft.Icons.SAVE, on_click=self._save)]),
                ft.Container(height=24),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            expand=True,
        )

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
            "aprsis_enabled": self.aprsis.value, "aprsis_host": self.is_host.value, "aprsis_port": self.is_port.value,
            "aprsis_passcode": self.passcode.value, "aprsis_radius_km": self.radius.value,
            "igate_rx": self.igate_rx.value, "igate_tx": self.igate_tx.value,
            "language": self.language.value or "",
            "check_updates": self.check_updates.value,
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
                if not licence_confirmed(self.licence.value):
                    raise ValueError(self.t("licence_required"))
                data["licence_confirmed"] = True
            conf = Config.from_dict(data).validate()
        except ValueError as err:
            self.error.value = f"{self.t('invalid')}: {err}"
            return
        self.error.value = ""
        await self.app.apply_config(conf)
        await asyncio.sleep(0)
