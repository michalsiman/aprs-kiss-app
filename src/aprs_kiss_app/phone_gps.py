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

    @property
    def wanted(self) -> bool:
        return self.app.mobile and self.app.engine.config.gps_source == "phone" and not self.app.engine.bbs_mode

    def _target(self) -> PushedGps | None:
        gps = self.app.engine.gps
        return gps if isinstance(gps, PushedGps) else None

    def sync(self, delay: float = 0) -> None:
        """After the start and after the settings change: start or stop following the location."""
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
            self.geo = fg.Geolocator(configuration=fg.GeolocatorConfiguration(
                accuracy=fg.GeolocatorPositionAccuracy.HIGH, distance_filter=0))
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
                    self._state(True)
                    first = await self._first_fix(ft, fg)
                    if first:
                        self._push(first)
                    return
            except Exception as err:  # noqa: BLE001 - shown to the user, then tried again
                _LOGGER.info("Phone location: %s", err)
                self._state(False, str(err) or type(err).__name__)
            await asyncio.sleep(RETRY_SECONDS)

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
