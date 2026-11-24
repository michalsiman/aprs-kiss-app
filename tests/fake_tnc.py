#!/usr/bin/env python3
"""A simulated KISS TNC on TCP, for trying the integration without a radio.

It plays the radio channel:
- every --interval seconds it "receives" an APRS packet (positions, a status,
  a message to our callsign) and sends it to the client;
- it answers APRS messages addressed to it with an ack;
- with --tak, TAK stations send positions and GeoChat (TAK Protocol v1 to TAK);
- it is a small BBS (OK0BBS by default) that accepts AX.25 connections and
  answers commands (H for help, L to list, B to say bye).

Run: python3 tests/fake_tnc.py --port 8001 --mycall OK1SIM-7
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))


def _load(name):
    return importlib.import_module(f"aprs_kiss_core.{name}")


ax25 = _load("ax25")
aprs = _load("aprs")
session = _load("session")
tak = _load("tak")
yapp = _load("yapp")

A = ax25.Address.parse

SAMPLES = [
    ("OK1ABC-9", "APRS", ["OK0DIG*", "WIDE2-1"], "=4945.12N/01322.50E>Mobile on the D5 motorway"),
    ("OK1XYZ", "APRS", ["WIDE1-1"], "!4935.00N/01245.00E-QTH Stod area"),
    ("OK2DEF-7", "APRS", ["OK0DIG*"], ">Listening on 144.800"),
    ("OK1WX", "APRS", [], "@161200z4936.50N/01310.00E_090/005g010t050r000p000P000h80b10150Weather"),
    ("OK1XYZ", "CQ", [], "Good evening, anyone on packet tonight?"),
    ("OK1KPL-10", "APRS", ["WIDE2-1"], "!4944.80NI01323.40E&iGate Plzen 144.800"),
    ("OK0DIG", "APRS", [], "!4951.20N/01306.00E#Digipeater Krasov"),
    ("OK1JKL-9", "APRS", ["OK0DIG*"], "=4939.60N/01328.90E>On the way to Klatovy"),
    ("OK1MNO-7", "APRS", ["WIDE1-1"], "=4948.30N/01317.20E[Hiking, 2 m handheld"),
    ("OK2PQR-5", "APRS", ["OK0DIG*", "WIDE2-1"], "=4933.10N/01309.80Eb Cycling around Prestice"),
]


def _pos(lat: float, lon: float, table: str = "/", code: str = ">") -> str:
    return f"{int(lat):02d}{(lat % 1) * 60:05.2f}N{table}{int(lon):03d}{(lon % 1) * 60:05.2f}E{code}"


def _obj(name: str, lat: float, lon: float, table: str, code: str, comment: str) -> str:
    return f";{name:<9}*111111z{_pos(lat, lon, table, code)}{comment}"


# --scene: a busy afternoon around Plzeň for the screenshots (repeaters with their frequency, road
# incidents, weather, a car with a trail), sent at once when the app connects
SCENE = [
    ("OK1KPL-10", "APRS", [], _obj("439.350MO", 49.7712, 13.4630, "/", "r", "439.350MHz T088 -760 OK0BPL Rokycany, FM + DMR CC1")),
    ("OK1KPL-10", "APRS", [], _obj("145.775PL", 49.6930, 13.2950, "/", "r", "145.775MHz T088 -600 OK0BL Plzen")),
    ("OK1KPL-10", "APRS", [], _obj("ER-OK0EB", 49.8400, 13.5600, "E", "0", "438.725MHz T077 R18k SvxLink, EchoLink")),
    ("OK1KPL-10", "APRS", [], _obj("OK0DSK B", 49.6600, 13.5300, "D", "a", "RNG0001 70cm Voice (D-Star) 438.600MHz -7.6000MHz")),
    ("OK1DOP-1", "APRS", [], _obj("D5 km 107", 49.7280, 13.2150, "\\", "'", "Nehoda, uzavren levy pruh / crash, left lane closed")),
    ("OK1DOP-1", "APRS", [], _obj("I26 prace", 49.7900, 13.4000, "\\", "j", "Prace na silnici, kyvadlovy provoz / road works")),
    ("OK1WX-13", "APRS", [], "@111111z" + _pos(49.7020, 13.4410, "/", "_") + "270/004g009t041r000p000P000h85b10142Rokycany WX"),
    ("OK1LOR-7", "APRS", ["WIDE1-1"], "=" + _pos(49.7600, 13.3100, "/", "[") + "Walking the dog"),
    ("OK1TRK-14", "APRS", ["OK0DIG*", "WIDE2-1"], "=" + _pos(49.6800, 13.4600, "/", "u") + "180/052Truck to Nepomuk"),
]
CAR_TRAIL = [(49.7440 + 0.0006 * k, 13.3950 + 0.0055 * k) for k in range(8)]  # OK1CAR-9 east of Plzeň


TAK_TEAM = [  # (uid, callsign, lat, lon, team, role)
    ("ANDROID-a1b2c3", "ALFA-1", 49.7620, 13.3450, "Cyan", "Team Lead"),
    ("ANDROID-d4e5f6", "ALFA-2", 49.7700, 13.3900, "Cyan", "Team Member"),
    ("ANDROID-0718aa", "MEDIC", 49.7330, 13.3980, "Red", "Medic"),
    ("ANDROID-99bb01", "RTO", 49.7290, 13.3420, "Green", "RTO"),
]
TAK_CHAT = [
    ("ANDROID-a1b2c3", "ALFA-1", "Checkpoint 2 reached, moving north"),
    ("ANDROID-0718aa", "MEDIC", "All OK here, standing by"),
    ("ANDROID-99bb01", "RTO", "Radio check, all stations report"),
]


class FakeTnc:
    def __init__(self, args):
        self.args = args
        self.writer = None
        self.bbs_call = A(args.bbs)
        self.sessions: dict[str, object] = {}
        self.msg_no = 0

    async def send_to_client(self, frame: ax25.Frame) -> None:
        if self.writer is not None:
            self.writer.write(ax25.kiss_frame(frame.encode()))
            await self.writer.drain()

    async def beacons(self):
        i = 0
        while True:
            await asyncio.sleep(self.args.interval)
            src, dst, path, info = SAMPLES[i % len(SAMPLES)]
            i += 1
            await self.send_to_client(ax25.Frame(A(dst), A(src), [A(p) for p in path], info.encode()))
            if i % 3 == 0:  # a car driving east from Plzeň towards Rokycany: its trail grows on the map
                step = (i // 3) % 40
                lat, lon = 49.745 + 0.0012 * step - 0.00002 * step * step, 13.40 + 0.012 * step
                pos = f"={int(lat):02d}{(lat % 1) * 60:05.2f}N/{int(lon):03d}{(lon % 1) * 60:05.2f}E>"
                await self.send_to_client(ax25.Frame(A("APRS"), A("OK1CAR-9"), [A("WIDE1-1")],
                                                     (pos + "On the road to Rokycany").encode()))
            if self.args.message_every and i % self.args.message_every == 0:
                self.msg_no += 1
                text = f":{aprs.addressee(self.args.mycall)}:Test message {self.msg_no} from the simulator{{{self.msg_no}"
                await self.send_to_client(ax25.Frame(A("APRS"), A("OK1ABC-9"), [A("WIDE1-1")], text.encode()))

    async def tak_traffic(self):
        """TAK stations around Plzeň: positions now and then, a GeoChat every third round (--tak)."""
        n = 0
        while True:
            for uid, call, lat, lon, team, role in TAK_TEAM:
                ev = tak.pli(uid, call, lat + 0.0007 * (n % 5), lon + 0.001 * (n % 3), team, role)
                await self.send_to_client(ax25.Frame(A(tak.DESTINATION), A("OK1ABC-9"), [], ev.encode()))
                await asyncio.sleep(1)
            if n % 3 == 0:
                uid, call, text = TAK_CHAT[(n // 3) % len(TAK_CHAT)]
                ev = tak.geochat(uid, call, text)
                await self.send_to_client(ax25.Frame(A(tak.DESTINATION), A("OK1ABC-9"), [], ev.encode()))
            n += 1
            await asyncio.sleep(self.args.interval)

    def bbs_session(self, remote: ax25.Address):
        key = str(remote)
        if key in self.sessions:
            return self.sessions[key]

        async def send(raw: bytes):
            await self.send_to_client(ax25.Frame.decode(raw))

        def on_text(text: str):
            for line in text.splitlines():
                cmd = line.strip().upper()
                if cmd.startswith("H"):
                    reply = "Commands: H help, L list messages, B bye\r"
                elif cmd.startswith("L"):
                    reply = "".join(f"{n:4d}  OK1XYZ  Test bulletin {n}\r" for n in range(1, 21))
                elif cmd.startswith("B"):
                    sess.send_text("73, bye\r")
                    asyncio.get_event_loop().call_later(2, sess.disconnect)
                    continue
                else:
                    reply = f"Unknown command: {line.strip()}\r"
                sess.send_text(reply + f"{self.bbs_call}> ")

        def on_state(state: str, reason: str):
            print(f"BBS session {key}: {state} ({reason})", flush=True)
            if state == "connected":
                sess.send_text(f"Welcome to {self.bbs_call}, the simulated BBS.\rType H for help.\r{self.bbs_call}> ")

        sess = session.Session(self.bbs_call, remote, [], send, on_text, on_state)
        self.sessions[key] = sess
        return sess

    async def handle_from_client(self, frame: ax25.Frame):
        print(f"<< {frame.monitor()}", flush=True)
        if frame.is_ui and frame.destination.call == "CQ" and frame.info:
            text = frame.info.decode("utf-8", "replace")
            await asyncio.sleep(3)
            reply = f"Hi {frame.source}, I copy you 5/9. You wrote: {text[:40]}"
            await self.send_to_client(ax25.Frame(A("CQ"), A("OK1XYZ"), [], reply.encode()))
            return
        if frame.is_ui and frame.info.startswith(b":"):
            body = frame.info.decode("latin-1")
            addressee, _, text = body[1:].partition(":")
            if addressee.strip() == "OK1ABC-9" and "{" in text and not text.startswith("ack"):
                no = text.rsplit("{", 1)[1]
                await asyncio.sleep(2)
                ack = f":{aprs.addressee(str(frame.source))}:ack{no}"
                await self.send_to_client(ax25.Frame(A("APRS"), A("OK1ABC-9"), [], ack.encode()))
            return
        if frame.destination == self.bbs_call and not frame.is_ui:
            self.bbs_session(frame.source).handle(frame)
        elif self.file_session is not None and frame.destination == self.file_session.me and not frame.is_ui:
            self.file_session.handle(frame)

    file_session = None

    async def send_file(self):
        """--send-file: OK1XYZ connects to us and sends a picture (YAPP), as another station would."""
        await asyncio.sleep(self.args.send_file)
        me, to = A("OK1XYZ"), A(self.args.mycall)

        async def send(raw: bytes):
            await self.send_to_client(ax25.Frame.decode(raw))

        data = bytes((i * 7 + i // 3) % 256 for i in range(36000))

        def on_state(state: str, reason: str):
            print(f"file session: {state} ({reason})", flush=True)
            if state == "connected":
                sender.start()

        sess = session.Session(me, to, [], send, lambda _t: None, on_state)
        sender = yapp.Sender("mapa-okoli.jpg", data, sess.send_bytes, lambda s, d: print("file:", s, d, flush=True))
        sess.on_data = sender.feed
        self.file_session = sess
        sess.connect()

    async def scene(self):
        await asyncio.sleep(1.5)
        for src, dst, path, info in SCENE:
            await self.send_to_client(ax25.Frame(A(dst), A(src), [A(p) for p in path], info.encode()))
            await asyncio.sleep(0.05)
        for src, dst, path, info in SAMPLES:
            await self.send_to_client(ax25.Frame(A(dst), A(src), [A(p) for p in path], info.encode()))
            await asyncio.sleep(0.05)
        for lat, lon in CAR_TRAIL:
            info = "=" + _pos(lat, lon) + "075/048On the road to Rokycany"
            await self.send_to_client(ax25.Frame(A("APRS"), A("OK1CAR-9"), [A("WIDE1-1")], info.encode()))
            await asyncio.sleep(0.6)

    async def client(self, reader, writer):
        print("client connected", flush=True)
        self.writer = writer
        if getattr(self.args, "scene", False):
            asyncio.ensure_future(self.scene())
        if getattr(self.args, "send_file", 0):
            asyncio.ensure_future(self.send_file())
        decoder = ax25.KissDecoder()
        try:
            while data := await reader.read(1024):
                for raw in decoder.feed(data):
                    await self.handle_from_client(ax25.Frame.decode(raw))
        finally:
            self.writer = None
            print("client disconnected", flush=True)

    async def run(self):
        server = await asyncio.start_server(self.client, "0.0.0.0", self.args.port)
        print(f"fake KISS TNC on :{self.args.port}, BBS {self.bbs_call}", flush=True)
        async with server:
            await asyncio.gather(server.serve_forever(), self.beacons(),
                                 *([self.tak_traffic()] if self.args.tak else []))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8001)
    p.add_argument("--mycall", default="OK1SIM-7")
    p.add_argument("--bbs", default="OK0BBS")
    p.add_argument("--interval", type=float, default=20)
    p.add_argument("--tak", action="store_true", help="also send TAK positions and GeoChat")
    p.add_argument("--message-every", type=int, default=3, help="a message to us every N packets, 0 = never")
    p.add_argument("--scene", action="store_true", help="send a busy area at once (for screenshots)")
    p.add_argument("--send-file", type=float, default=0, help="N seconds after the app connects, send it a file (YAPP)")
    asyncio.run(FakeTnc(p.parse_args()).run())
