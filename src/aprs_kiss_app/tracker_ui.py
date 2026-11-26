"""The "my position" button in the top bar: send it once now, or run the tracker.

While the tracker runs the button is green with a ▶ next to the pin (amber while it waits for the GPS
or for transmitting to be switched on); the menu then offers ⏸ to stop it.
"""

from __future__ import annotations

import flet as ft

from .views.base import check_item


def _mmss(seconds: float) -> str:
    seconds = max(0, round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class PositionButton:
    def __init__(self, app, compact: bool) -> None:
        self.app = app
        t = app.t
        self.pin = ft.Icon(ft.Icons.SHARE_LOCATION, size=16 if compact else 22, color=ft.Colors.ON_SURFACE)
        self.play = ft.Icon(ft.Icons.PLAY_ARROW, size=14 if compact else 18, visible=False)
        face = ft.Row([self.pin, self.play], spacing=0, tight=True,
                      vertical_alignment=ft.CrossAxisAlignment.CENTER)
        # a lamp like the others in the top bar (larger on a computer)
        self.face = ft.Container(face, height=26 if compact else 36, alignment=ft.Alignment.CENTER,
                                 padding=ft.Padding.symmetric(horizontal=6 if compact else 10),
                                 border_radius=5 if compact else 7,
                                 border=ft.Border.all(1.5 if compact else 2.0, ft.Colors.OUTLINE))
        self.send_item = ft.PopupMenuItem(t("pos_send_now"), icon=ft.Icons.SEND, on_click=self._send_now)
        self.toggle_item = ft.PopupMenuItem(t("trk_start"), icon=ft.Icons.PLAY_ARROW, on_click=self._toggle)
        self.state_item = ft.PopupMenuItem(t("trk_off"), disabled=True)
        settings = ft.PopupMenuItem(t("trk_settings"), icon=ft.Icons.TUNE, on_click=lambda _e: app.select("settings"))
        # warnings while the tracker runs (both off until switched on here or in Settings › Tracker)
        conf = app.engine.config
        self.road_item, self.road_box = check_item(t("trk_menu_road"), ft.Icons.CAR_CRASH_OUTLINED, conf.road_alerts,
                                                   lambda _e: self._flip("road_alerts"))
        self.meet_item, self.meet_box = check_item(t("trk_menu_meet"), ft.Icons.PEOPLE_OUTLINE, conf.meet_alerts,
                                                   lambda _e: self._flip("meet_alerts"))
        self.control = ft.PopupMenuButton(content=self.face, tooltip=t("beacon_now"),
                                          items=[self.send_item, self.toggle_item, ft.PopupMenuItem(),
                                                 self.state_item, self.road_item, self.meet_item, settings],
                                          on_open=self._opened)
        self.control.visible = not app.engine.exclusive_mode
        self.refresh()

    def state_text(self) -> tuple[str, str | None]:
        """(text, colour) of the tracker's state."""
        st = self.app.engine.tracker_status()
        t = self.app.t
        if not st["on"]:
            return t("trk_off"), None
        if not st["gps"]:
            return t("trk_wait_gps"), ft.Colors.AMBER
        if not st["can_send"]:
            return t("trk_wait_tx"), ft.Colors.AMBER
        return t("trk_running", t=_mmss(st["next_in"] or 0)), ft.Colors.GREEN

    def refresh(self) -> None:
        on = self.app.engine.config.tracker_on
        text, color = self.state_text()
        self.play.visible = on
        self.pin.color = self.play.color = color or ft.Colors.ON_SURFACE
        if isinstance(self.face.border, ft.Border):
            self.face.border = ft.Border.all(self.face.border.top.width, color or ft.Colors.OUTLINE)
        self.toggle_item.content = self.app.t("trk_stop" if on else "trk_start")
        self.toggle_item.icon = ft.Icons.PAUSE if on else ft.Icons.PLAY_ARROW
        self.state_item.content = text
        self.road_box.value = self.app.engine.config.road_alerts
        self.meet_box.value = self.app.engine.config.meet_alerts
        self.control.tooltip = text if on else self.app.t("beacon_now")

    async def _send_now(self, e) -> None:
        await self.app._beacon_now(e)

    def _toggle(self, _e) -> None:
        app, engine = self.app, self.app.engine
        conf = engine.config
        if conf.tracker_on:
            engine.set_tracking(False)
            app.toast(app.t("trk_stopped"))
        else:
            if engine.gps is None:  # a position typed in, no GPS: nothing to follow
                app.toast(app.t("trk_no_gps"), error=True, seconds=8)
                return
            engine.set_tracking(True)
            hints = [app.t("trk_started")]
            if not engine.station.tx_enabled:
                hints.append(app.t("trk_wait_tx"))
            if app.mobile and not conf.run_background:
                hints.append(app.t("trk_bg_hint"))
            app.toast(" ".join(hints), seconds=8 if len(hints) > 1 else 4)
        app.save_config_soon()
        self.refresh()
        app.page.update()

    def _flip(self, name: str) -> None:
        conf = self.app.engine.config
        setattr(conf, name, not getattr(conf, name))
        self.app.save_config_soon()
        self.refresh()
        self.app.page.update()

    def _opened(self, _e) -> None:
        self.refresh()  # the countdown as it is now
        self.app.page.update()
