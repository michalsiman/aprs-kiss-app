"""A pretend VARA FM for tests and for trying the terminal without a radio.

Speaks VARA's TCP interface ("VARA Protocol Native TNC Commands", EA5HVK): the command port takes
MYCALL, LISTEN, CONNECT, DISCONNECT, ABORT… and answers OK; a CONNECT to any callsign except
NOANSWER is answered with PENDING then CONNECTED, and the data port then runs a tiny BBS.

Run: python3 tests/fake_vara.py --port 8300      (data port 8301)
"""

from __future__ import annotations

import argparse
import asyncio


class FakeVara:
    def __init__(self, delay: float = 0.3) -> None:
        self.delay = delay
        self.commands: list[str] = []
        self.received = b""
        self._cmd: asyncio.StreamWriter | None = None
        self._data: asyncio.StreamWriter | None = None
        self._pending: asyncio.Task | None = None
        self.mycall = ""

    def _say(self, line: str) -> None:
        if self._cmd:
            self._cmd.write(line.encode() + b"\r")

    def _send(self, text: str) -> None:
        if self._data:
            self._data.write(text.replace("\n", "\r").encode())

    async def command_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._cmd = writer
        buf = b""
        while chunk := await reader.read(1024):
            buf += chunk
            while b"\r" in buf:
                raw, buf = buf.split(b"\r", 1)
                line = raw.decode().strip()
                if line:
                    self.commands.append(line)
                    await self._handle(line)
            await writer.drain()
        self._cmd = None

    async def data_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._data = writer
        buf = b""
        while chunk := await reader.read(1024):
            self.received += chunk
            buf += chunk
            while b"\r" in buf:
                raw, buf = buf.split(b"\r", 1)
                cmd = raw.decode(errors="replace").strip().upper()
                if cmd == "B":
                    self._send("73, bye\r")
                    await asyncio.sleep(self.delay)
                    self._say("DISCONNECTED")
                elif cmd == "L":
                    self._send("  1 OK1XYZ  Test bulletin over VARA\r  2 OK1ABC  Net tonight\rVARA BBS>\r")
                else:
                    self._send(f"Commands: L list, B bye\rVARA BBS>\r")
            await writer.drain()
        self._data = None

    async def _handle(self, line: str) -> None:
        word, _, rest = line.partition(" ")
        word = word.upper()
        if word == "MYCALL":
            self.mycall = rest.split()[0] if rest else ""
        if word == "CONNECT":
            self._say("OK")
            parts = rest.split()
            self._pending = asyncio.ensure_future(self._connect(parts[0], parts[1]))
            return
        if word in ("DISCONNECT", "ABORT"):
            self._say("OK")
            if self._pending:
                self._pending.cancel()
            await asyncio.sleep(self.delay / 3)
            self._say("DISCONNECTED")
            return
        self._say("OK")

    async def _connect(self, source: str, dest: str) -> None:
        await asyncio.sleep(self.delay)
        self._say("PENDING")
        await asyncio.sleep(self.delay)
        if dest.upper() == "NOANSWER":
            self._say("CANCELPENDING")
            self._say("DISCONNECTED")
            return
        self._say(f"CONNECTED {source} {dest}")
        if self._cmd:
            await self._cmd.drain()
        await asyncio.sleep(self.delay / 3)
        self._send(f"[VARA-BBS] Welcome {source} to {dest}\rVARA BBS>\r")
        if self._data:
            await self._data.drain()


async def serve(port: int, fake: FakeVara) -> tuple[asyncio.AbstractServer, asyncio.AbstractServer]:
    cmd = await asyncio.start_server(fake.command_client, "127.0.0.1", port)
    data = await asyncio.start_server(fake.data_client, "127.0.0.1", port + 1)
    return cmd, data


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8300)
    args = p.parse_args()
    cmd, data = await serve(args.port, FakeVara(delay=1.0))
    print(f"fake VARA on 127.0.0.1:{args.port} (data {args.port + 1})", flush=True)
    async with cmd, data:
        await asyncio.gather(cmd.serve_forever(), data.serve_forever())


if __name__ == "__main__":
    asyncio.run(main())
