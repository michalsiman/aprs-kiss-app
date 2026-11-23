"""Short beeps: when the radio transmits, when a message, a chat line or a TAK GeoChat comes in.

Each one can be switched on or off in Settings › Sounds. The tones are made here (small WAV files
in memory) and played through Flet's Audio service, on phones and computers alike.
"""

from __future__ import annotations

import io
import logging
import math
import struct
import time
import wave
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import App

_LOGGER = logging.getLogger(__name__)
RATE = 22050

# (frequency Hz, milliseconds) pieces; 0 Hz is silence
TONES = {
    "tx": [(1200, 60)],  # a short click-like beep: the radio keyed up
    "message": [(660, 90), (0, 40), (990, 140)],  # rising two-tone: an APRS message for you
    "chat": [(880, 70), (0, 40), (880, 70)],  # two short beeps: someone on packet chat
    "tak": [(990, 70), (0, 30), (1320, 70), (0, 30), (1760, 110)],  # rising three: TAK GeoChat
}
SETTING = {"tx": "sound_tx", "message": "sound_messages", "chat": "sound_chat", "tak": "sound_tak"}
MIN_GAP = {"tx": 1.0, "message": 2.0, "chat": 2.0, "tak": 2.0}  # seconds between two of the same kind


def wav(pieces: list[tuple[int, int]], volume: float = 0.5) -> bytes:
    """A mono 16-bit WAV of the tones, each with a short fade in and out (no clicks)."""
    frames = bytearray()
    for freq, ms in pieces:
        n = int(RATE * ms / 1000)
        fade = max(1, min(n // 4, int(RATE * 0.008)))
        for i in range(n):
            env = min(1.0, i / fade, (n - 1 - i) / fade)
            value = math.sin(2 * math.pi * freq * i / RATE) * volume * env if freq else 0.0
            frames += struct.pack("<h", int(value * 32767))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    return out.getvalue()


class Sounds:
    def __init__(self, app: App) -> None:
        self.app = app
        self.players: dict = {}
        self.last: dict[str, float] = {}

    def wanted(self, kind: str) -> bool:
        return bool(getattr(self.app.engine.config, SETTING[kind], False))

    def on_event(self, kind: str, data: dict) -> None:
        """Engine events → sounds."""
        if kind == "monitor":
            line = data.get("line", "")
            if " >> " in line[:12] and "[IS] " not in line[12:18]:  # sent by radio, not to APRS-IS
                self.play("tx")
        elif kind == "message":
            self.play("message")
        elif kind == "chat" and not data.get("entry", {}).get("out"):
            self.play("chat")
        elif kind == "tak" and data.get("chat") and not data["chat"].get("out"):
            self.play("tak")

    def play(self, kind: str, force: bool = False) -> None:
        if not force and not self.wanted(kind):
            return
        now = time.monotonic()
        if not force and now - self.last.get(kind, -99) < MIN_GAP[kind]:
            return
        self.last[kind] = now
        try:
            self.app.page.run_task(self._play, kind)
        except Exception:  # noqa: BLE001 - the page is gone
            pass

    async def _play(self, kind: str) -> None:
        try:
            player = self.players.get(kind)
            if player is None:
                import flet_audio as fa  # noqa: PLC0415

                player = self.players[kind] = fa.Audio(src=wav(TONES[kind]), release_mode=fa.ReleaseMode.STOP)
                self.app.page.update()
            await player.play()
        except Exception as err:  # noqa: BLE001 - no sound is not worth an error message
            _LOGGER.info("Sound %s: %s", kind, err)
