"""TAK: TAK Protocol v1 encoding (checked against takproto by hand), GeoChat, and the engine's TAK mode."""

import asyncio
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core import tak  # noqa: E402
from aprs_kiss_core.ax25 import Address, Frame  # noqa: E402
from aprs_kiss_core.config import Config  # noqa: E402
from aprs_kiss_core.engine import Engine, TransmitRefused  # noqa: E402

# A PLI as takproto.xml2proto() writes it for an ATAK event (callsign PEPA, team Red, battery 77).
ATAK_PLI = bytes.fromhex(
    "bf01bf129e010a09612d662d472d552d432a0b414e44524f49442d61626330808d97a6a03438808d97a6a03440c0dcbb"
    "a6a0344a036d2d67518fc2f5285ccf48405952b81e85eb512a4061000000000000794069000000000000244071000000"
    "00000024407a3d12110a092a3a2d313a737463701204504550411a100a0352656412095465616d204c6561642a02084d"
    "3a12090000000000000040110000000000805640"
)


class CodecTest(unittest.TestCase):
    def test_pli_round_trip(self):
        ev = tak.pli("OK1SIM-14", "OK1SIM", 49.6203, 13.1627, team="Cyan", hae=412.0, speed=1.5, course=87.0,
                     now=1795400000)
        raw = ev.encode()
        self.assertTrue(raw.startswith(tak.MESH_HEADER))
        self.assertLessEqual(len(raw), tak.MAX_PAYLOAD)
        back = tak.decode(raw)
        self.assertEqual((back.type, back.uid, back.callsign, back.team, back.role),
                         ("a-f-G-U-C", "OK1SIM-14", "OK1SIM", "Cyan", "Team Member"))
        self.assertAlmostEqual(back.lat, 49.6203)
        self.assertEqual((back.hae, back.speed, back.course), (412.0, 1.5, 87.0))
        self.assertEqual(back.stale_ms - back.time_ms, 600000)

    def test_reads_what_atak_sends(self):
        ev = tak.decode(ATAK_PLI)
        self.assertEqual((ev.uid, ev.callsign, ev.team, ev.role), ("ANDROID-abc", "PEPA", "Red", "Team Lead"))
        self.assertEqual((ev.lat, ev.lon, ev.hae, ev.speed, ev.course, ev.battery), (49.62, 13.16, 400.0, 2.0, 90.0, 77))

    def test_geochat(self):
        evs = tak.geochat_events("OK1SIM-14", "OK1SIM", "Sraz u kóty 412 v 10:00 & díky")
        self.assertEqual(len(evs), 1)
        back = tak.decode(evs[0].encode())
        self.assertEqual(back.type, "b-t-f")
        self.assertEqual(back.extra, {"chatroom": "All", "sender": "OK1SIM", "to": "All",
                                      "text": "Sraz u kóty 412 v 10:00 & díky"})
        long = tak.geochat_events("OK1SIM-14", "OK1SIM", "slyšíš mě dobře? " * 30)
        self.assertGreater(len(long), 1)
        self.assertTrue(all(len(e.encode()) <= tak.MAX_PAYLOAD for e in long))
        text = " ".join(tak.decode(e.encode()).extra["text"] for e in long)
        self.assertEqual(text.split(), ("slyšíš mě dobře? " * 30).split())

    def test_full_atak_geochat_is_read(self):
        detail = ('<__chat parent="RootContactGroup" chatroom="All Chat Rooms" id="All Chat Rooms" '
                  'senderCallsign="PEPA"><chatgrp uid0="ANDROID-abc" uid1="All Chat Rooms"/></__chat>'
                  '<remarks source="BAO.F.ATAK.ANDROID-abc" to="All Chat Rooms" time="x">Ahoj &amp; čau</remarks>')
        self.assertEqual(tak.read_chat(detail)["text"], "Ahoj & čau")
        self.assertEqual(tak.read_chat(detail)["sender"], "PEPA")

    def test_garbage(self):
        for bad in (b"", b"\xbf\x01\xbf\xff\xff", b"hello", b"\xbf\x02\xbf"):
            with self.assertRaises(ValueError):
                tak.decode(bad)


class EngineTakTest(unittest.IsolatedAsyncioTestCase):
    async def test_tak_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            eng = Engine(Config(callsign="OK1SIM-14", latitude=49.62, longitude=13.16, tak_enabled=True,
                                tak_team="Red", aprsis_enabled=True, licence_confirmed=True).validate(),
                         pathlib.Path(tmp))
            sent = []

            async def send_frame(raw):
                sent.append(Frame.decode(raw))

            eng.send_frame = send_frame
            self.assertEqual(eng.exclusive_mode, "tak")
            self.assertIsNone(eng.aprsis)
            with self.assertRaises(TransmitRefused):
                await eng.send_aprs_message("OK1ABC", "hi")
            # a station and a message heard on the radio
            pepa = tak.pli("OK1PEP-9", "PEPA", 49.7, 13.4, team="Blue")
            eng._on_frame(Frame(Address.parse("TAK"), Address.parse("OK1PEP-9"), [], pepa.encode()).encode())
            msg = tak.geochat_events("OK1PEP-9", "PEPA", "jsem na místě")[0]
            eng._on_frame(Frame(Address.parse("TAK"), Address.parse("OK1PEP-9"), [], msg.encode()).encode())
            self.assertEqual(eng.tak_stations["OK1PEP-9"]["callsign"], "PEPA")
            self.assertEqual(eng.tak_stations["OK1PEP-9"]["team"], "Blue")
            self.assertEqual([c["text"] for c in eng.tak_chat], ["jsem na místě"])
            # APRS is ignored in TAK mode
            eng._on_frame(Frame(Address.parse("APRS"), Address.parse("OK1XYZ"), [], b"!4942.00N/01318.00E-").encode())
            self.assertEqual(eng.station.heard, {})
            # sending
            await eng.send_tak_position()
            await eng.send_tak_chat("rozumím", "OK1PEP-9", "PEPA")
            self.assertEqual([str(f.destination) for f in sent], ["TAK", "TAK"])
            me = tak.decode(sent[0].info)
            self.assertEqual((me.uid, me.team, me.callsign), ("OK1SIM-14", "Red", "OK1SIM-14"))
            self.assertEqual(tak.decode(sent[1].info).extra["to"], "OK1PEP-9")
            self.assertTrue(eng.tak_chat[-1]["out"])
            self.assertTrue(any("TAK PLI PEPA (Blue, Team Member) 49.70000 13.40000" in line for line in eng.monitor))
            self.assertTrue(any("TAK GeoChat PEPA → All: jsem na místě" in line for line in eng.monitor))


    async def test_tak_frames_are_not_aprs_outside_tak_mode(self):
        # A TAK PLI whose protobuf bytes happen to look like an APRS position must not become a station.
        with tempfile.TemporaryDirectory() as tmp:
            eng = Engine(Config(callsign="OK1SIM-7", latitude=49.62, longitude=13.16).validate(), pathlib.Path(tmp))
            for i in range(20):
                ev = tak.pli(f"ANDROID-{i:06x}", f"T{i}", 49.6 + i / 100, 13.1, team="Cyan")
                eng._on_frame(Frame(Address.parse("TAK"), Address.parse("OK1ABC-9"), [], ev.encode()).encode())
            self.assertEqual(eng.station.heard, {})
            self.assertEqual(list(eng.chat), [])
            self.assertTrue(any("TAK PLI T0" in line for line in eng.monitor))


if __name__ == "__main__":
    unittest.main()
