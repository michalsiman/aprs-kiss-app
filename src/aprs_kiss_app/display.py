"""The station server's own screen (/display): a dashboard for a small display next to the radio – a Raspberry Pi
with a 5" or 7" screen (800×480 and up) in a kiosk browser. Big lamps (TNC, APRS-IS, digipeater, transmitting),
counters, and the last frames heard, the stations, the messages or the bulletins, chosen by a tap. Everything
else is set over the web, from a phone or a computer."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
import time
from typing import Any

import flet as ft

from aprs_kiss_core import packetinfo, units

from . import i18n, shared

_LOGGER = logging.getLogger(__name__)

TABS = ("frames", "stations", "messages", "bulletins")
ROWS = 30
ON = ft.Colors.GREEN_400
OFF = ft.Colors.with_opacity(0.35, ft.Colors.ON_SURFACE)
TX_ON = ft.Colors.RED_400


def local_address() -> str:
    """This computer's address in the local network (no packet is sent: a UDP socket only picks a route)."""
    with contextlib.suppress(OSError), socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("192.0.2.1", 9))  # TEST-NET-1: never routed anywhere, only the route is looked up
        return s.getsockname()[0]
    return socket.gethostname()


def path_text(path: list[str]) -> str:
    return ",".join(p for p in path if p and p.upper() not in ("TCPIP", "TCPIP*")) if path else ""


class Display:
    def __init__(self, page: ft.Page, engine) -> None:
        self.page, self.engine = page, engine
        conf = engine.config
        self.t = i18n.Translator(conf.language)
        units.current = units.Units.choose(conf.units_distance, conf.units_temperature, i18n.system_country(),
                                           comma=self.t.language != "en", pressure=conf.units_pressure)
        self.tab = "frames"
        self.dirty = True
        self.closed = False
        self._remove = engine.add_listener(self._on_event)

    # ─── building ────────────────────────────────────────────────────────

    def _lamp(self, label: str) -> tuple[ft.Container, ft.Icon, ft.Text]:
        dot = ft.Icon(ft.Icons.CIRCLE, size=14, color=OFF)
        state = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
        box = ft.Container(
            ft.Row([ft.Text(label, size=14, color=ft.Colors.ON_SURFACE_VARIANT, expand=True), dot, state],
                   spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8), border_radius=8, expand=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH)
        return box, dot, state

    def _tile(self, label: str) -> tuple[ft.Container, ft.Text]:
        value = ft.Text("0", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        box = ft.Container(
            ft.Column([ft.Text(label, size=12, color=ft.Colors.ON_SURFACE_VARIANT), value], spacing=0,
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(vertical=6), border_radius=8, expand=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH)
        return box, value

    def build(self) -> ft.Control:
        t = self.t
        self.title = ft.Text("", size=24, weight=ft.FontWeight.BOLD, expand=True, no_wrap=True)
        self.clock = ft.Text("", size=22, weight=ft.FontWeight.W_500)
        self.tnc_box, self.tnc_dot, self.tnc_state = self._lamp("TNC")
        self.is_box, self.is_dot, self.is_state = self._lamp("APRS-IS")
        self.digi_box, self.digi_dot, self.digi_state = self._lamp("DIGI")
        self.tx_box, self.tx_dot, self.tx_state = self._lamp("TX")
        self.tx_box.on_click = lambda _e: self._toast(t("disp_tx_hold"))
        self.tx_box.on_long_press = self._toggle_tx
        self.tnc_detail = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT, expand=True, no_wrap=True)
        self.last_rf = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        tiles = [self._tile(t(k)) for k in ("disp_rx", "disp_tx", "disp_igate", "disp_digi", "stations")]
        self.counts = [v for _box, v in tiles]
        self.tabs = ft.SegmentedButton(
            selected=[self.tab], show_selected_icon=False, on_change=self._pick_tab,
            segments=[ft.Segment(value=k, label=ft.Text(t(f"disp_tab_{k}"), size=13)) for k in TABS])
        self.head = ft.Row(spacing=8)
        self.rows = ft.ListView(spacing=0, expand=True)
        self.footer = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT, expand=True, no_wrap=True)
        self.note = ft.Text("", size=12, color=ft.Colors.PRIMARY)
        return ft.Container(
            ft.Column([
                ft.Row([self.title, self.clock], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([self.tnc_box, self.is_box, self.digi_box, self.tx_box], spacing=8),
                ft.Row([self.tnc_detail, self.last_rf]),
                ft.Row([box for box, _v in tiles], spacing=8),
                ft.Row([self.tabs], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(ft.Column([self.head, ft.Divider(height=1), self.rows], spacing=4, expand=True),
                             expand=True, border_radius=8, padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                             bgcolor=ft.Colors.SURFACE_CONTAINER_LOW),
                ft.Row([self.footer, self.note]),
            ], spacing=8, expand=True),
            padding=ft.Padding.all(10), expand=True)

    # ─── updating ────────────────────────────────────────────────────────

    def _on_event(self, kind: str, _data: dict[str, Any]) -> None:
        if kind in ("packet", "message", "bulletin", "aprs_message", "update", "monitor"):
            self.dirty = True

    def _pick_tab(self, e) -> None:
        self.tab = next(iter(e.control.selected), "frames")
        self.dirty = True
        self.refresh()

    def _toast(self, text: str) -> None:
        self.note.value = text
        self._note_until = time.monotonic() + 4
        self.page.update()

    def _toggle_tx(self, _e) -> None:
        self.engine.set_tx(not self.engine.tx_enabled)
        self._toast(self.t("tx_on") if self.engine.tx_enabled else self.t("tx_off"))
        self.refresh()

    @staticmethod
    def _light(dot: ft.Icon, state: ft.Text, on: bool, text: str, color=ON) -> None:
        dot.color = color if on else OFF
        state.value = text
        state.color = color if on else ft.Colors.ON_SURFACE_VARIANT

    def refresh(self) -> None:
        eng, t = self.engine, self.t
        st = eng.status()
        conf = eng.config
        now = time.time()
        self.title.value = f"{st['callsign'] or '—'} · APRS & Packet"
        self.clock.value = time.strftime("%H:%M:%S")
        self._light(self.tnc_dot, self.tnc_state, st["tnc_connected"],
                    t("connected") if st["tnc_connected"] else t("disconnected"))
        where = {"tcp": f"{conf.host}:{conf.port}", "serial": conf.device, "direwolf": "Direwolf"}.get(conf.connection, "")
        self.tnc_detail.value = f"TNC: {where}" + (f" – {t.error(st['tnc_error'])}" if st.get("tnc_error") and not
                                                   st["tnc_connected"] else "")
        aprsis = st["aprsis"]
        self._light(self.is_dot, self.is_state, bool(aprsis and aprsis["verified"]),
                    "ON" if aprsis and aprsis["verified"] else ("…" if aprsis else "OFF"))
        digi = conf.digi_mode != "off" and not eng.exclusive_mode
        self._light(self.digi_dot, self.digi_state, digi, conf.digi_mode.upper() if digi else "OFF")
        self._light(self.tx_dot, self.tx_state, st["tx_enabled"], "ON" if st["tx_enabled"] else "OFF", TX_ON)
        self.tx_box.border = ft.Border.all(2, TX_ON) if st["tx_enabled"] else None
        stats, igate = st["stats"], st["igate_stats"]
        values = (stats.get("received", 0), stats.get("sent", 0), igate.get("rf_to_is", 0), st["digipeated"],
                  len(eng.station.heard))
        for text, value in zip(self.counts, values):
            text.value = str(value)
        last = eng.recent_rf[-1]["received_at"] if eng.recent_rf else None
        self.last_rf.value = t("disp_last_rf", t=time.strftime("%H:%M:%S", time.localtime(last))) if last else ""
        url = shared.STATE.get("url") or f"http://{local_address()}:{shared.STATE.get('port', 8080)}"
        self.footer.value = t("disp_web", url=url)
        if getattr(self, "_note_until", 0) and time.monotonic() > self._note_until:
            self.note.value, self._note_until = "", 0
        if self.dirty:
            self.dirty = False
            self._fill(now)
        self.page.update()

    def _cells(self, values: list[tuple[str, int | None]], bold: bool = False, color=None) -> ft.Row:
        return ft.Row([ft.Text(v, size=13, width=w, expand=w is None, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                               weight=ft.FontWeight.BOLD if bold else None,
                               color=color or (ft.Colors.ON_SURFACE_VARIANT if bold else None))
                       for v, w in values], spacing=8)

    def _fill(self, now: float) -> None:
        t, eng = self.t, self.engine
        hhmm = lambda ts: time.strftime("%H:%M:%S", time.localtime(ts)) if ts else ""  # noqa: E731
        weather = self._weather
        if self.tab == "frames":
            head = [(t("disp_time"), 70), (t("disp_call"), 100), (t("disp_type"), 80), (t("disp_path"), 120),
                    (t("disp_content"), None)]
            rows = [[(hhmm(p.get("received_at")), 70), (p.get("from", ""), 100),
                     (t(f"disp_kind_{packetinfo.kind(p)}"), 80),
                     (path_text(p.get("path") or []) or t("disp_direct"), 120),
                     (packetinfo.summary(p, weather), None)] for p in reversed(eng.recent_rf)]
        elif self.tab == "stations":
            head = [(t("disp_call"), 110), (t("disp_heard"), 80), (t("disp_distance"), 80), (t("disp_content"), None)]
            here = eng.my_position()
            entries = sorted(eng.station.heard.values(), key=lambda e: e.get("last_heard", 0), reverse=True)
            rows = []
            for e in entries[:ROWS]:
                km = ""
                if here and e.get("latitude") is not None:
                    from aprs_kiss_core.tracker import distance_m  # noqa: PLC0415
                    km = units.current.distance_short(distance_m(*here, e["latitude"], e["longitude"]) / 1000)
                rows.append([(e.get("from") or e.get("call") or "", 110), (t.age(now - e.get("last_heard", now)), 80),
                             (km, 80), ((e.get("comment") or e.get("status") or "").strip(), None)])
        elif self.tab == "messages":
            head = [(t("disp_time"), 70), (t("disp_call"), 100), (t("to"), 100), (t("text"), None)]
            rows = [[(hhmm(m.get("time")), 70), (m.get("from", ""), 100), (m.get("to", ""), 100), (m.get("text", ""), None)]
                    for m in reversed(list(eng.messages)[-ROWS:])]
        else:
            head = [(t("disp_time"), 70), (t("disp_call"), 100), ("BLN", 80), (t("text"), None)]
            rows = [[(hhmm(b.get("time")), 70), (b.get("from", ""), 100), (b.get("addressee", ""), 80), (b.get("text", ""), None)]
                    for b in eng.bulletins_shown()[:ROWS]]
        self.head.controls = self._cells(head, bold=True).controls
        self.rows.controls = [ft.Container(self._cells(r), padding=ft.Padding.symmetric(vertical=3),
                                           border=ft.Border.only(bottom=ft.BorderSide(
                                               1, ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE))))
                              for r in rows[:ROWS]] or [ft.Text(t("disp_none"), color=ft.Colors.ON_SURFACE_VARIANT)]

    @staticmethod
    def _weather(w: dict[str, Any]) -> str:
        parts = []
        if w.get("temperature") is not None:
            parts.append(units.current.temperature_text(w["temperature"]))
        if w.get("humidity") is not None:
            parts.append(f"{w['humidity']:.0f} %")
        if w.get("pressure") is not None:
            parts.append(units.current.pressure_text(w["pressure"]))
        return " · ".join(parts)

    async def run(self) -> None:
        while not self.closed:
            try:
                self.refresh()
            except Exception:  # noqa: BLE001 - the clock must go on; a gone page ends the loop below
                if getattr(getattr(self.page, "session", None), "connection", True) is None:
                    break
                _LOGGER.exception("Display")
            await asyncio.sleep(1)
        self.close()

    def close(self) -> None:
        self.closed = True
        self._remove()


async def main(page: ft.Page) -> None:
    """/display: the dashboard, dark, the whole screen."""
    engine = shared.engine()
    page.title = "APRS & Packet"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    page.bgcolor = ft.Colors.SURFACE
    display = Display(page, engine)
    page.on_close = lambda _e: display.close()
    page.add(display.build())
    await display.run()
