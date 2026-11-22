"""Ties the TNC connection, the APRS station, APRS-IS and the terminal sessions together.

The standalone counterpart of the Home Assistant integration's hub.py. It knows
nothing about any user interface: everything that happens is announced to the
listeners added with `add_listener(callback)` as `callback(kind, data)`:

    "monitor"       {"line": str}                   one frame, TNC style
    "terminal"      {"entry": {...}}                text of a connected session
    "state"         {"remote": str, "state": str}   a session changed state
    "chat"          {"entry": {...}}                packet chat line
    "aprs_message"  {"message": {...}}              an APRS message in or out (history item)
    "message"       {...}                           an APRS message addressed to us (for notifications)
    "packet"        {...}                           every decoded APRS packet
    "update"        {}                              something in the status changed

All of it runs on one asyncio event loop; listeners are called on that loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import aprs as aprs_build
from . import thursday
from .aprsis import AprsIsClient, gate_to_is, passcode, third_party
from .ax25 import PF, U_DM, Address, Frame
from .config import MIN_BEACON_MINUTES, VERSION, Config, load_state, save_state
from .connection import KissConnection, TncSettings
from .parser import parse
from .session import DISCONNECTED, Session
from .station import Station, StationConfig, TransmitRefused

_LOGGER = logging.getLogger(__name__)

MONITOR_LINES = 500
THURSDAY_LINES = 300
THURSDAY_DUPLICATE_SECONDS = 15 * 60
TERMINAL_LINES = 2000
MESSAGE_HISTORY = 500
CHAT_LINES = 500
CHAT_DUPLICATE_SECONDS = 30
# A station counts as local (for gating internet messages to RF) if heard on RF this recently.
LOCAL_SECONDS = 1800
SAVE_DELAY = 5.0
# First character of an APRS information field (APRS 1.0.1, data type identifiers).
APRS_TYPES = set("!=/@;)`':>?<$_{}*#")
# Packet chat is text meant for people: frames to these, or to our own callsign. Automatic
# frames (a digipeater's "DX de ..." report to DX, station IDs to ID or BEACON) stay in the monitor.
CHAT_DESTINATIONS = {"CQ", "QST", "ALL"}

Listener = Callable[[str, dict[str, Any]], None]

__all__ = ["Engine", "TransmitRefused"]


class Engine:
    """One TNC with one callsign."""

    def __init__(self, config: Config, data_folder: Path | None = None) -> None:
        self.config = config
        self._folder = data_folder
        self._listeners: list[Listener] = []
        self._msg_counter = 0
        self.messages: deque[dict[str, Any]] = deque(maxlen=MESSAGE_HISTORY)
        self.monitor: deque[str] = deque(maxlen=MONITOR_LINES)
        self.monitor_rf: deque[str] = deque(maxlen=MONITOR_LINES)  # the same without APRS-IS lines
        self.terminal: deque[dict[str, Any]] = deque(maxlen=TERMINAL_LINES)
        self.chat: deque[dict[str, Any]] = deque(maxlen=CHAT_LINES)
        # #APRSThursday: the HOTG group's traffic and ANSRVR's answers, kept out of the inbox.
        self.thursday: deque[dict[str, Any]] = deque(maxlen=THURSDAY_LINES)
        self.thursday_joined = 0.0  # when we last sent a CQ to HOTG (0 = not in the group)
        self.thursday_cq = 0.0  # the last CQ, for the server's one-per-30-minutes rule
        self._thursday_recent: dict[str, float] = {}
        self._chat_recent: dict[str, float] = {}
        self.sessions: dict[str, Session] = {}
        self.igate_stats = {"rf_to_is": 0, "is_to_rf": 0, "is_messages": 0}
        self._tasks: set[asyncio.Task] = set()
        self._beacon_task: asyncio.Task | None = None
        self._save_handle: asyncio.TimerHandle | None = None
        self._loaded = False
        self.running = False
        self._build(tx_enabled=False)

    # ─── listeners ────────────────────────────────────────────────────────

    def add_listener(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener) if listener in self._listeners else None

    def _emit(self, kind: str, data: dict[str, Any] | None = None) -> None:
        for listener in list(self._listeners):
            try:
                listener(kind, data or {})
            except Exception:  # noqa: BLE001 - a broken listener must not stop the radio
                _LOGGER.exception("Listener failed on %s", kind)

    # ─── building from the config ─────────────────────────────────────────

    def _build(self, tx_enabled: bool) -> None:
        conf = self.config
        self.me = Address.parse(conf.callsign or "NOCALL")
        self.accept_incoming = conf.accept_incoming
        self.igate_rx = conf.igate_rx
        self.igate_tx = conf.igate_tx
        self.connection = KissConnection(
            TncSettings(kind=conf.connection, host=conf.host, port=int(conf.port), device=conf.device,
                        baudrate=int(conf.baudrate), txdelay_ms=conf.txdelay_ms or None),
            self._on_frame,
            self._on_connection_state,
        )
        self.station = Station(
            StationConfig(str(self.me), conf.paths(), conf.symbol, conf.comment),
            self.send_frame, parse, self._on_packet, self._on_message, self._on_update, self._next_msg_number,
        )
        self.station.tx_enabled = tx_enabled
        self.aprsis: AprsIsClient | None = None
        if conf.aprsis_on and conf.callsign:
            radius = int(conf.aprsis_radius_km or 0)
            code = conf.aprsis_passcode or passcode(str(self.me))
            area = (f"r/{conf.latitude:.3f}/{conf.longitude:.3f}/{radius}"
                    if radius > 0 and conf.has_position else "")
            self.aprsis = AprsIsClient(
                conf.aprsis_host, int(conf.aprsis_port), str(self.me), int(code), area,
                f"aprs-kiss {VERSION}", self._on_is_line, self._on_is_state,
            )
            self.station.send_is = self._send_own_to_is

    # ─── lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        if not self._loaded:
            stored = await asyncio.to_thread(load_state, self._folder)
            self._msg_counter = int(stored.get("msg_counter", 0))
            self.messages.extend(stored.get("messages", []))
            self.thursday.extend(stored.get("thursday", []))
            self.thursday_joined = float(stored.get("thursday_joined", 0) or 0)
            self.thursday_cq = float(stored.get("thursday_cq", 0) or 0)
            self._loaded = True
        self.running = True
        if not self.config.configured:
            self._on_update()
            return  # nothing to connect to before the callsign is set
        await self.connection.start()
        if self.aprsis:
            await self.aprsis.start()
        if self.config.beacon_minutes:
            self._beacon_task = asyncio.create_task(self._beacon_loop(), name="aprs_kiss_beacon")
        self._on_update()

    async def stop(self) -> None:
        self.running = False
        for s in self.sessions.values():
            s.close()
        self.sessions.clear()
        if self._beacon_task:
            self._beacon_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._beacon_task
            self._beacon_task = None
        for task in list(self._tasks):
            task.cancel()
        await self.station.close()
        if self.aprsis:
            await self.aprsis.stop()
        await self.connection.stop()
        await self.save()

    async def reconfigure(self, config: Config) -> None:
        """Apply new settings: stop, rebuild, start again. History and the Transmit switch stay."""
        tx = self.station.tx_enabled and config.callsign == self.config.callsign
        await self.stop()
        self.config = config
        self._build(tx_enabled=tx)
        await self.start()

    async def save(self) -> None:
        if self._save_handle:
            self._save_handle.cancel()
            self._save_handle = None
        await asyncio.to_thread(save_state, self._state(), self._folder)

    def _state(self) -> dict[str, Any]:
        return {"msg_counter": self._msg_counter, "messages": list(self.messages), "thursday": list(self.thursday),
                "thursday_joined": self.thursday_joined, "thursday_cq": self.thursday_cq}

    def _schedule_save(self) -> None:
        if self._save_handle:
            return
        loop = asyncio.get_running_loop()
        self._save_handle = loop.call_later(SAVE_DELAY, lambda: self._spawn(self.save()))

    def _spawn(self, coro) -> None:
        task = asyncio.get_running_loop().create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _next_msg_number(self) -> int:
        self._msg_counter += 1
        self._schedule_save()
        return self._msg_counter

    # ─── status ───────────────────────────────────────────────────────────

    @property
    def tx_enabled(self) -> bool:
        return self.station.tx_enabled

    def set_tx(self, enabled: bool) -> None:
        self.station.tx_enabled = bool(enabled) and self.config.configured
        self._on_update()

    def status(self) -> dict[str, Any]:
        return {
            "callsign": str(self.me) if self.config.configured else "",
            "tnc_connected": self.connection.connected,
            "tnc_error": self.connection.last_error,
            "tx_enabled": self.station.tx_enabled,
            "aprsis": {
                "connected": self.aprsis.connected,
                "verified": self.aprsis.verified,
                "server": self.aprsis.server_name,
                "error": self.aprsis.last_error,
            } if self.aprsis else None,
            "igate_stats": dict(self.igate_stats),
            "stats": dict(self.station.stats),
            "sessions": self.session_states(),
        }

    # ─── sending ──────────────────────────────────────────────────────────

    async def send_frame(self, raw: bytes) -> None:
        """Every transmission goes through here: refused while transmitting is off."""
        if not self.station.tx_enabled:
            raise TransmitRefused("Transmitting is switched off")
        await self.connection.send(raw)
        self._monitor(Frame.decode(raw).monitor(), outgoing=True)

    async def _send_quietly(self, raw: bytes) -> None:
        try:
            await self.send_frame(raw)
        except (TransmitRefused, ConnectionError) as err:
            _LOGGER.debug("Frame not sent: %s", err)

    # ─── receiving ────────────────────────────────────────────────────────

    def _on_frame(self, raw: bytes) -> None:
        try:
            frame = Frame.decode(raw)
        except ValueError as err:
            self._monitor(f"? undecodable frame ({err}): {raw.hex()}")
            return
        self._monitor(frame.monitor())
        if frame.is_ui:
            self._chat_frame(frame)
            self.station.handle_frame(raw)
            return
        if frame.destination != self.me:
            return
        key = str(frame.source)
        sess = self.sessions.get(key)
        back = [Address(d.call, d.ssid) for d in reversed(frame.path)]
        if sess is None or sess.state == DISCONNECTED:
            if frame.kind == "SABM" and self.accept_incoming and self.station.tx_enabled:
                sess = self._new_session(frame.source, back)
            elif frame.kind == "SABM" or (frame.command and frame.poll_final):
                if self.station.tx_enabled:
                    reply = Frame(frame.source, self.me, back, b"", U_DM | (PF if frame.poll_final else 0), None, False)
                    self._spawn(self._send_quietly(reply.encode()))
                return
            elif sess is None:
                return
        sess.handle(frame)

    def _monitor(self, line: str, outgoing: bool = False) -> None:
        entry = f"{time.strftime('%H:%M:%S')} {'>>' if outgoing else '<<'} {line}"
        self.monitor.append(entry)
        if not line.startswith("[IS] "):
            self.monitor_rf.append(entry)
        self._emit("monitor", {"line": entry})

    def _on_packet(self, packet: dict[str, Any]) -> None:
        self._emit("packet", packet)
        if self.igate_rx and self.aprsis and self.aprsis.verified:
            src, _, rest = packet["raw"].partition(">")
            dst = rest.split(",", 1)[0].split(":", 1)[0]
            info = rest.split(":", 1)[1].encode("latin-1", "replace") if ":" in rest else b""
            line = gate_to_is(src, dst, list(packet.get("path", [])), info, str(self.me))
            if line:
                self._spawn(self._gate_up(line))

    async def _gate_up(self, line: str) -> None:
        if self.aprsis and await self.aprsis.send(line):
            self._monitor(f"[IS] {line}", outgoing=True)
            self.igate_stats["rf_to_is"] += 1
            self._on_update()

    # ─── APRS-IS ──────────────────────────────────────────────────────────

    async def _send_own_to_is(self, info: str) -> bool:
        if not self.aprsis or not self.aprsis.verified:
            return False
        line = f"{self.me}>{aprs_build.TOCALL},TCPIP*:{info}"
        sent = await self.aprsis.send(line)
        if sent:
            self._monitor(f"[IS] {line}", outgoing=True)
        return sent

    def _on_is_state(self, connected: bool) -> None:
        self._on_update()

    def _on_is_line(self, line: str, garbled: bool = False) -> None:
        self._monitor(f"[IS] {line}")
        packet = parse(line)
        packet["raw"] = line
        if garbled:
            packet["garbled"] = True
        head = line.partition(":")[0]
        packet["path"] = head.split(",")[1:] or ["TCPIP"]
        src = packet.get("from", "")
        if self.station.handle_is_packet(packet):
            self.igate_stats["is_messages"] += 1
            return
        if not self.igate_tx or packet.get("format") != "message":
            return
        to = (packet.get("addresse") or "").strip().upper()
        local = self.station.heard.get(to)
        now = time.time()
        if not local or now - local.get("last_rf", 0) > LOCAL_SECONDS:  # heard by the radio lately
            return
        src_local = self.station.heard.get(src.upper())
        if src_local and now - src_local.get("last_rf", 0) < LOCAL_SECONDS:
            return  # the sender is on RF itself
        head, _, info = line.partition(":")
        dst = head.split(">", 1)[1].split(",", 1)[0] if ">" in head else "APRS"
        self._spawn(self._gate_down(third_party(src, dst, info, str(self.me))))

    async def _gate_down(self, info: str) -> None:
        try:
            await self.station.send_info(info, rf=True, to_is=False)
            self.igate_stats["is_to_rf"] += 1
        except (TransmitRefused, ConnectionError) as err:
            _LOGGER.debug("Internet message not sent on RF: %s", err)
        self._on_update()

    # ─── beacon ───────────────────────────────────────────────────────────

    async def _beacon_loop(self) -> None:
        interval = max(MIN_BEACON_MINUTES, int(self.config.beacon_minutes)) * 60
        while True:
            await asyncio.sleep(interval)
            await self.beacon()

    async def beacon(self) -> None:
        """Our position: by radio while transmitting is on; over the internet only when chosen."""
        if not self.config.has_position:
            _LOGGER.debug("Beacon not sent: no position set")
            return
        try:
            await self.station.send_position(self.config.latitude, self.config.longitude,
                                             to_is=self.config.beacon_is)
        except (TransmitRefused, ConnectionError) as err:
            _LOGGER.debug("Beacon not sent: %s", err)

    async def send_position(self, lat: float | None = None, lon: float | None = None,
                            comment: str | None = None) -> None:
        lat = self.config.latitude if lat is None else lat
        lon = self.config.longitude if lon is None else lon
        if lat is None or lon is None:
            raise ValueError("No position set")
        await self.station.send_position(lat, lon, comment)

    async def send_status(self, text: str) -> None:
        await self.station.send_status(text)

    # ─── APRS messages ────────────────────────────────────────────────────

    def _on_message(self, message: dict[str, Any]) -> None:
        if thursday.is_server(message["from"]) or thursday.is_group_text(message.get("text", "")):
            self._thursday_in(message)
            return
        item = {"direction": "in", "from": message["from"], "to": str(self.me), "text": message["text"],
                "time": message["received_at"], "msg_no": message.get("msg_no"), "via": message.get("via")}
        self.messages.append(item)
        self._schedule_save()
        self._emit("message", message)
        self._emit("aprs_message", {"message": item})

    # ─── #APRSThursday ────────────────────────────────────────────────────

    def _thursday_in(self, message: dict[str, Any]) -> None:
        """A HOTG message passed on by ANSRVR (from the original sender), or ANSRVR's own answer."""
        now = message.get("received_at") or time.time()
        text = message.get("text", "")
        key = f"{message['from'].upper()}|{text}"
        for k in [k for k, t in self._thursday_recent.items() if now - t > THURSDAY_DUPLICATE_SECONDS]:
            del self._thursday_recent[k]
        if key in self._thursday_recent:  # the same relay heard by radio and over the internet
            return
        self._thursday_recent[key] = now
        server = thursday.is_server(message["from"])
        if server and text.lower().startswith("removed from"):
            self.thursday_joined = 0.0
        entry = {"time": now, "from": message["from"], "text": text if server else thursday.strip_prefix(text),
                 "kind": "server" if server else "in", "via": message.get("via")}
        self._thursday_add(entry)

    def _thursday_add(self, entry: dict[str, Any]) -> None:
        self.thursday.append(entry)
        self._schedule_save()
        self._emit("thursday", {"entry": entry})

    def thursday_member_until(self, now: float | None = None) -> float:
        """Until when ANSRVR keeps us in HOTG (0 = not a member)."""
        until = self.thursday_joined + thursday.MEMBER_SECONDS if self.thursday_joined else 0.0
        return until if until > (now or time.time()) else 0.0

    def thursday_wait(self, now: float | None = None) -> float:
        """Seconds before the server takes another CQ from us."""
        return max(0.0, self.thursday_cq + thursday.CQ_INTERVAL - (now or time.time()))

    async def send_thursday(self, text: str, via: str = "both") -> dict[str, Any]:
        """Check in: "CQ HOTG <text>" to ANSRVR, which passes it on to the group and adds us to it."""
        if not text.strip():
            raise ValueError("Empty message")
        wait = self.thursday_wait()
        if wait:
            raise ValueError(f"ANSRVR takes one message every 30 minutes; wait {int(wait // 60) + 1} min")
        msg = await self.station.send_message(thursday.SERVER, thursday.compose(text), via=via)
        now = time.time()
        self.thursday_cq = self.thursday_joined = now
        self._thursday_add({"time": now, "from": str(self.me), "text": thursday.strip_prefix(msg.text),
                            "kind": "out", "msg_no": msg.msg_id, "via": via})
        return msg.as_dict()

    async def leave_thursday(self, via: str = "both") -> None:
        """Leave HOTG ("U HOTG"), so the group's messages stop coming."""
        msg = await self.station.send_message(thursday.SERVER, f"U {thursday.GROUP}", via=via)
        self.thursday_joined = 0.0
        self._thursday_add({"time": time.time(), "from": str(self.me), "text": msg.text, "kind": "leave",
                            "msg_no": msg.msg_id, "via": via})

    def _on_connection_state(self, connected: bool) -> None:
        self._on_update()

    def _on_update(self) -> None:
        self._emit("update")

    async def send_aprs_message(self, to: str, text: str, via: str = "both") -> dict[str, Any]:
        msg = await self.station.send_message(to, text, via=via)
        item = {"direction": "out", "from": str(self.me), "to": msg.to, "text": msg.text, "time": msg.created,
                "msg_no": msg.msg_id, "via": via}
        self.messages.append(item)
        self._schedule_save()
        self._emit("aprs_message", {"message": item})
        return msg.as_dict()

    def message_state(self, msg_no: str | None) -> str | None:
        msg = self.station.outgoing.get(str(msg_no)) if msg_no else None
        return msg.state if msg else None

    # ─── terminal sessions ────────────────────────────────────────────────

    def _new_session(self, remote: Address, path: list[Address]) -> Session:
        key = str(remote)
        old = self.sessions.pop(key, None)
        if old:
            old.close()

        def on_text(text: str) -> None:
            self._terminal(key, "rx", text)

        def on_state(state: str, reason: str) -> None:
            self._terminal(key, "state", reason or state)
            self._emit("state", {"remote": key, "state": state})
            self._on_update()

        sess = Session(self.me, remote, path, self.send_frame, on_text, on_state)
        self.sessions[key] = sess
        return sess

    def _terminal(self, remote: str, kind: str, text: str) -> None:
        entry = {"time": time.time(), "remote": remote, "kind": kind, "text": text}
        self.terminal.append(entry)
        self._emit("terminal", {"entry": entry})

    def connect(self, remote: str, path: str = "") -> None:
        if not self.station.tx_enabled:
            raise TransmitRefused("Transmitting is switched off")
        if not self.connection.connected:
            raise ConnectionError("The TNC is not connected")
        addr = Address.parse(remote)
        paths = Config(path=path).paths()
        sess = self._new_session(addr, [Address.parse(p) for p in paths])
        sess.connect()

    def disconnect(self, remote: str) -> None:
        sess = self.sessions.get(str(Address.parse(remote)))
        if sess:
            sess.disconnect()

    def send_text(self, remote: str, text: str) -> None:
        key = str(Address.parse(remote))
        sess = self.sessions.get(key)
        if sess is None:
            raise ConnectionError("Not connected")
        sess.send_text(text)
        self._terminal(key, "tx", text)

    def session_states(self) -> dict[str, str]:
        return {k: s.state for k, s in self.sessions.items() if s.state != DISCONNECTED}

    # ─── chat (plain text in UI frames) ───────────────────────────────────

    @staticmethod
    def is_aprs(frame: Frame) -> bool:
        info = frame.info
        return frame.destination.call.startswith("AP") or (bool(info) and chr(info[0]) in APRS_TYPES)

    def _chat_frame(self, frame: Frame) -> None:
        # Packet chat only: APRS packets never show up in the chat.
        if not frame.info or frame.source == self.me or self.is_aprs(frame):
            return
        if frame.destination.call not in CHAT_DESTINATIONS and frame.destination != self.me:
            return
        now = time.time()
        key = f"{frame.source}|{frame.info!r}"
        for k in [k for k, t in self._chat_recent.items() if now - t > CHAT_DUPLICATE_SECONDS]:
            del self._chat_recent[k]
        if key in self._chat_recent:
            return
        self._chat_recent[key] = now
        text = frame.info.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n").strip()
        prefix = f"{frame.source}: "
        if text.upper().startswith(prefix.upper()):
            text = text[len(prefix):]
        self._chat_add({"time": now, "from": str(frame.source), "to": str(frame.destination),
                        "text": text, "out": False})

    def _chat_add(self, entry: dict[str, Any]) -> None:
        self.chat.append(entry)
        self._emit("chat", {"entry": entry})

    async def send_chat(self, text: str) -> None:
        """Packet chat: just the text in a UI frame to CQ, direct (no digipeaters, nothing of APRS)."""
        text = text.strip()
        if not text:
            return
        await self.send_unproto("CQ", text)
        self._chat_add({"time": time.time(), "from": str(self.me), "to": "CQ", "text": text, "out": True})

    async def send_unproto(self, destination: str, text: str, path: str = "") -> None:
        """A UI frame with plain text (classic unproto, e.g. to CQ or ID)."""
        frame = Frame(Address.parse(destination or "CQ"), self.me,
                      [Address.parse(p) for p in Config(path=path).paths()], text.replace("\n", "\r").encode("utf-8"))
        await self.send_frame(frame.encode())
