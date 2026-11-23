"""Settings of one station and where the app keeps its files.

Replaces Home Assistant's config entry: a plain dataclass saved as JSON.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from .aprsis import DEFAULT_PORT as DEFAULT_APRSIS_PORT
from .aprsis import DEFAULT_SERVER as DEFAULT_APRSIS_HOST
from .ax25 import Address

_LOGGER = logging.getLogger(__name__)

APP_NAME = "aprs-kiss"
VERSION = "0.1.26"
MIN_BEACON_MINUTES = 10


@dataclass
class Config:
    """Everything the user can set. Field names match the Home Assistant integration."""

    # TNC
    connection: str = "tcp"  # a transport registered in connection.py
    host: str = "127.0.0.1"
    port: int = 8001
    device: str = ""
    baudrate: int = 9600
    txdelay_ms: int = 0  # 0 = leave the TNC's own
    # Station
    callsign: str = ""
    path: str = "WIDE1-1,WIDE2-1"
    symbol: str = "/-"
    comment: str = ""
    latitude: float | None = None  # our position (Home Assistant's home in the integration)
    longitude: float | None = None
    beacon_minutes: int = 0
    beacon_is: bool = False
    tracked_callsigns: str = ""
    accept_incoming: bool = False
    # APRS-IS
    aprsis_enabled: bool = False
    licence_confirmed: bool = False
    aprsis_host: str = DEFAULT_APRSIS_HOST
    aprsis_port: int = DEFAULT_APRSIS_PORT
    aprsis_passcode: str = ""
    aprsis_radius_km: int = 50
    igate_rx: bool = False
    igate_tx: bool = False
    # App
    language: str = ""  # "", "cs" or "en"; empty = from the system
    show_internet: bool = True  # map and station list also show stations seen only on APRS-IS
    monitor_internet: bool = True  # the frame monitor also shows APRS-IS lines ([IS])
    map_muted: bool = False  # map tiles faded, so the station labels stand out
    map_offline: bool = False  # the bundled offline map (borders, cities) instead of OpenStreetMap tiles
    gps_source: str = "manual"  # "manual" (latitude/longitude above), "usb" (an NMEA GPS module), "phone"
    gps_device: str = ""  # its serial port
    gps_baudrate: int = 0  # 0 = find it automatically
    tak_enabled: bool = False  # TAK mode: only TAK positions and GeoChat over the radio
    tak_callsign: str = ""  # TAK callsign shown to others; empty = the station callsign
    tak_team: str = "Cyan"
    tak_role: str = "Team Member"
    tak_interval_min: int = 2  # own position every N minutes (0 = only when asked)
    vara_host: str = ""  # VARA FM's address for the terminal (empty = no VARA)
    vara_port: int = 8300  # its command port; the data port is the next one
    bbs_enabled: bool = False  # run the BBS server (its own SSID, below)
    bbs_ssid: int = 1  # the BBS answers on your callsign with this SSID
    bbs_list: str = ""  # saved BBSes and nodes for the terminal: JSON [{"call": ..., "path": ...}]
    check_updates: bool = True  # ask GitHub once a day whether a newer version is out
    theme: str = "auto"  # auto (as the desktop), light, dark

    @property
    def configured(self) -> bool:
        return bool(self.callsign)

    @property
    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def aprsis_on(self) -> bool:
        return self.aprsis_enabled and self.licence_confirmed

    def paths(self) -> list[str]:
        return [p.strip().upper() for p in (self.path or "").replace(" ", ",").split(",") if p.strip()]

    def validate(self) -> Config:
        """Normalise and check; raises ValueError with a short reason."""
        if self.callsign:
            self.callsign = str(Address.parse(self.callsign.strip()))
        for p in self.paths():
            Address.parse(p)
        self.path = ",".join(self.paths())
        if len(self.symbol) != 2:
            raise ValueError("The symbol is two characters: table and code")
        if self.aprsis_passcode and not str(self.aprsis_passcode).lstrip("-").isdigit():
            raise ValueError("The passcode is a number")
        for name in ("latitude", "longitude"):
            value = getattr(self, name)
            if value in ("", None):
                setattr(self, name, None)
                continue
            value = float(value)
            if abs(value) > (90 if name == "latitude" else 180):
                raise ValueError(f"Invalid {name}")
            setattr(self, name, value)
        if self.beacon_minutes and self.beacon_minutes < MIN_BEACON_MINUTES:
            self.beacon_minutes = MIN_BEACON_MINUTES
        if self.connection == "tcp" and not (0 < int(self.port) < 65536):
            raise ValueError("Invalid TCP port")
        if not self.aprsis_enabled:
            self.licence_confirmed = False
        return self

    def saved_bbs(self) -> list[dict[str, str]]:
        """The terminal's saved stations, each {"call", "path"}, in the order they were saved."""
        try:
            items = json.loads(self.bbs_list) if self.bbs_list else []
        except ValueError:
            return []
        out = []
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and str(item.get("call", "")).strip():
                out.append({"call": str(item["call"]).strip().upper(), "path": str(item.get("path", "")).strip().upper()})
        return out

    def save_bbs(self, call: str, path: str = "") -> None:
        """Add a station, or update its path when it is already saved."""
        call, path = call.strip().upper(), path.strip().upper()
        items = [i for i in self.saved_bbs() if i["call"] != call]
        items.append({"call": call, "path": path})
        self.bbs_list = json.dumps(items)

    def remove_bbs(self, call: str) -> None:
        self.bbs_list = json.dumps([i for i in self.saved_bbs() if i["call"] != call.strip().upper()])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Unknown keys are ignored, values are coerced to the field's type."""
        out = cls()
        for f in fields(cls):
            if f.name not in data:
                continue
            value = data[f.name]
            default = getattr(out, f.name)
            try:
                if value is None or value == "":
                    value = None if f.name in ("latitude", "longitude") else ("" if isinstance(default, str) else default)
                elif isinstance(default, bool):
                    value = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
                elif isinstance(default, int):
                    value = int(value)
                elif f.name in ("latitude", "longitude"):
                    value = float(value)
                else:
                    value = str(value)
            except (TypeError, ValueError):
                value = default
            setattr(out, f.name, value)
        return out


def data_dir() -> Path:
    """A writable folder for settings and history.

    Apps built with `flet build` (also on Android/iOS) get FLET_APP_STORAGE_DATA;
    otherwise the usual per-user folder (~/.local/share/aprs-kiss on Linux,
    %LOCALAPPDATA%\\aprs-kiss on Windows). APRS_KISS_DATA overrides both.
    """
    for var in ("APRS_KISS_DATA", "FLET_APP_STORAGE_DATA"):
        if os.environ.get(var):
            path = Path(os.environ[var])
            break
    else:
        from platformdirs import user_data_dir  # noqa: PLC0415

        path = Path(user_data_dir(APP_NAME, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as err:
        _LOGGER.warning("Could not read %s: %s", path, err)
        return None


def load_config(folder: Path | None = None) -> Config:
    data = _read_json((folder or data_dir()) / "config.json")
    return Config.from_dict(data) if isinstance(data, dict) else Config()


def save_config(config: Config, folder: Path | None = None) -> None:
    _write_json((folder or data_dir()) / "config.json", config.to_dict())


def load_state(folder: Path | None = None) -> dict[str, Any]:
    data = _read_json((folder or data_dir()) / "state.json")
    return data if isinstance(data, dict) else {}


def save_state(state: dict[str, Any], folder: Path | None = None) -> None:
    _write_json((folder or data_dir()) / "state.json", state)
