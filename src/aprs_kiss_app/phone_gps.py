"""The phone's own location (Android, iOS) as "my position", through Flet's Geolocator.

Settings › GPS › "The phone's GPS". The app asks for the location permission, then follows the
position stream and hands every fix to the engine (aprs_kiss_core.gps.PushedGps), which uses it
for the map and the beacon just like a USB GPS module.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aprs_kiss_core.gps import PushedGps

if TYPE_CHECKING:
    from .app import App

_LOGGER = logging.getLogger(__name__)
RETRY_SECONDS = 15  # location switched off or permission refused: look again this often


class PhoneGps:
    def __init__(self, app: App) -> None:
        self.app = app
        self.geo = None
        self.running = False
        self.last: dict | None = None  # the last fix, handed again to a rebuilt engine
        self._task: asyncio.Task | None = None
        self._background_on = False

    @property
    def background(self) -> bool:
        """Android: keep running when the app is not on screen (a foreground service with a notification)."""
        return self.app.android and self.app.engine.config.run_background

    @property
    def wanted(self) -> bool:
        conf = self.app.engine.config
        return self.app.mobile and not self.app.engine.bbs_mode and (conf.gps_source == "phone" or self.background)

    def _settings(self):
        import flet as ft  # noqa: PLC0415
        import flet_geolocator as fg  # noqa: PLC0415

        if not self.background:
            return fg.GeolocatorConfiguration(accuracy=fg.GeolocatorPositionAccuracy.HIGH, distance_filter=0)
        t = self.app.t
        return background_settings(ft, fg)(
            accuracy=fg.GeolocatorPositionAccuracy.HIGH, distance_filter=0,
            interval_duration=ft.Duration(seconds=10),
            foreground_notification_title="APRS & Packet",
            foreground_notification_text=t("bg_notification"),
            foreground_notification_channel_name=t("bg_channel"),
            foreground_notification_enable_wake_lock=True,  # the CPU keeps running: receiving, beacons, TAK
            foreground_notification_enable_wifi_lock=True,
            foreground_notification_set_ongoing=True,
        )

    def _target(self) -> PushedGps | None:
        gps = self.app.engine.gps
        return gps if isinstance(gps, PushedGps) else None

    def sync(self, delay: float = 0) -> None:
        """After the start and after the settings change: start or stop following the location."""
        if self.wanted and self.running and self.geo is not None and self._background_on != self.background:
            self._background_on = self.background
            self.geo.configuration = self._settings()
            self.geo.update()  # the stream starts again, with or without the foreground service
            self._restyle_soon()
        if self.wanted:
            target = self._target()
            if target and self.last and self.running:
                target.push(**self.last)  # the engine was rebuilt: it gets the last fix at once
            if not self._task or self._task.done():
                self._task = self.app.page.run_task(self._start, delay)
        elif self.running or (self._task and not self._task.done()):
            if self._task:
                self._task.cancel()
            self._stop()

    def _state(self, ok: bool, error: str = "") -> None:
        target = self._target()
        if target:
            target.set_state(ok, error)

    async def _start(self, delay: float = 0) -> None:
        import flet as ft  # noqa: PLC0415
        import flet_geolocator as fg  # noqa: PLC0415 - only on phones

        await asyncio.sleep(delay)
        t = self.app.t
        if self.geo is None:
            self._background_on = self.background
            self.geo = fg.Geolocator(configuration=self._settings())
        while self.wanted and not self.running:
            try:
                status = await self.geo.request_permission()
                if status in (fg.GeolocatorPermissionStatus.DENIED, fg.GeolocatorPermissionStatus.DENIED_FOREVER):
                    self._state(False, t("gps_phone_denied"))
                elif not await self.geo.is_location_service_enabled():
                    self._state(False, t("gps_phone_off"))
                else:
                    self.running = True
                    self.geo.on_position_change = self._position
                    self.geo.on_error = self._error
                    self.geo.update()  # with a handler set, the phone starts sending positions
                    self._restyle_soon()
                    self._state(True)
                    first = await self._first_fix(ft, fg)
                    if first:
                        self._push(first)
                    return
            except Exception as err:  # noqa: BLE001 - shown to the user, then tried again
                _LOGGER.info("Phone location: %s", err)
                self._state(False, str(err) or type(err).__name__)
            await asyncio.sleep(RETRY_SECONDS)

    def _restyle_soon(self) -> None:
        if self.background:
            self.app.page.run_task(self._restyle)

    async def _restyle(self) -> None:
        """The service's notification with our icon, once the service has posted it."""
        from .android_notify import restyle_service_notification  # noqa: PLC0415

        for wait in (1, 2, 3, 5, 10):
            await asyncio.sleep(wait)
            if restyle_service_notification():
                return

    async def _first_fix(self, ft, fg):
        """A position at once (the phone's last known one), before the stream sends its first."""
        for ask in (self.geo.get_last_known_position,
                    lambda: self.geo.get_current_position(fg.GeolocatorConfiguration(
                        accuracy=fg.GeolocatorPositionAccuracy.HIGH, time_limit=ft.Duration(seconds=20)))):
            try:
                found = await ask()
            except Exception as err:  # noqa: BLE001 - the stream will bring one
                _LOGGER.info("Phone location, first fix: %s", err)
                continue
            if found and found.latitude is not None:
                return found
        return None

    def _stop(self) -> None:
        self.running = False
        if self.geo is not None:
            self.geo.on_position_change = None
            self.geo.on_error = None
            self.geo.update()  # no handlers: the phone stops sending

    def _position(self, e) -> None:
        self._push(e.position)

    def _push(self, p) -> None:
        if p is None or p.latitude is None or p.longitude is None:
            return
        self.last = {"latitude": float(p.latitude), "longitude": float(p.longitude), "altitude_m": p.altitude,
                     "speed_ms": p.speed, "course": p.heading, "accuracy_m": p.accuracy}
        target = self._target()
        if target:
            target.push(**self.last)

    def _error(self, e) -> None:
        _LOGGER.info("Phone location error: %s", e.data)
        self._state(False, str(e.data or ""))
        # e.g. location switched off: wait for it to come back
        self.running = False
        self._stop()
        self.sync(delay=RETRY_SECONDS)


_BACKGROUND_SETTINGS = None


def background_settings(ft, fg):
    """Android position-stream settings that start the geolocator's foreground service.

    flet-geolocator 1.1.2 sends ForegroundNotificationConfiguration as a nested object, but its Dart side
    reads flat "foreground_notification_*" keys, so the service never started. These flat fields are what
    it reads. The service (with its notification and a wake lock) keeps the app, and so the radio link,
    running while it is not on screen.
    """
    global _BACKGROUND_SETTINGS
    if _BACKGROUND_SETTINGS is None:
        @ft.value
        class BackgroundSettings(fg.GeolocatorAndroidConfiguration):
            # None by default: Flet sends only values that differ from the default, so every value
            # given here goes out
            foreground_notification_title: str | None = None
            foreground_notification_text: str | None = None
            foreground_notification_channel_name: str | None = None
            foreground_notification_enable_wake_lock: bool | None = None
            foreground_notification_enable_wifi_lock: bool | None = None
            foreground_notification_set_ongoing: bool | None = None

        _BACKGROUND_SETTINGS = BackgroundSettings
    return _BACKGROUND_SETTINGS
