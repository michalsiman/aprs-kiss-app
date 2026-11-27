"""The engine against the simulated TNC: receive, messages with ack, a BBS session, saved state."""

import argparse
import asyncio
import pathlib
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core.config import Config, load_config, load_state, save_config  # noqa: E402
from aprs_kiss_core.engine import Engine, TransmitRefused  # noqa: E402

from tests.fake_tnc import FakeTnc  # noqa: E402

MYCALL = "OK1SIM-7"


async def wait_for(check, timeout=15.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check():
            return True
        await asyncio.sleep(0.05)
    return False


class EngineTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = pathlib.Path(self.tmp.name)
        self.tnc = FakeTnc(argparse.Namespace(port=0, mycall=MYCALL, bbs="OK0BBS", interval=0.1, message_every=3))
        self.server = await asyncio.start_server(self.tnc.client, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        self.beacons = asyncio.create_task(self.tnc.beacons())
        conf = Config(callsign=MYCALL, host="127.0.0.1", port=port, latitude=49.7, longitude=13.4).validate()
        self.engine = Engine(conf, self.folder)
        self.events: list[tuple[str, dict]] = []
        self.engine.add_listener(lambda kind, data: self.events.append((kind, data)))
        await self.engine.start()
        self.assertTrue(await wait_for(lambda: self.engine.connection.connected))

    async def asyncTearDown(self):
        await self.engine.stop()
        self.beacons.cancel()
        self.server.close()
        self.tmp.cleanup()

    def kinds(self):
        return [k for k, _ in self.events]

    async def test_receives_stations_and_messages(self):
        self.assertTrue(await wait_for(lambda: "OK1ABC-9" in self.engine.station.heard
                                       and any(m["direction"] == "in" for m in self.engine.messages)))
        heard = self.engine.station.heard["OK1ABC-9"]
        self.assertAlmostEqual(heard["latitude"], 49.752, places=2)
        self.assertIn("monitor", self.kinds())
        self.assertIn("message", self.kinds())
        self.assertTrue(await wait_for(lambda: any(e["text"].startswith("Good evening") for e in self.engine.chat)))

    async def test_monitor_keeps_radio_lines_apart_from_aprs_is(self):
        self.assertTrue(await wait_for(lambda: len(self.engine.monitor_rf) >= 2))
        for i in range(600):  # a busy APRS-IS feed must not push the radio frames out
            self.engine._on_is_line(f"OK{i}XYZ>APRS,TCPIP*,qAC,T2CZECH:>test {i}")
        self.assertTrue(all("[IS] " not in line for line in self.engine.monitor_rf))
        self.assertGreaterEqual(len(self.engine.monitor_rf), 2)
        self.assertTrue(all("[IS] " in line for line in list(self.engine.monitor)[-500:]))

    async def test_chat_shows_only_frames_meant_for_people(self):
        from aprs_kiss_core.ax25 import Address, Frame

        def ui(src, dst, text):
            return Frame(Address.parse(dst), Address.parse(src), [], text.encode()).encode()

        self.engine._on_frame(ui("OK0BAD-2", "DX", "DX de OK0BAD-2>144800.0  OK0DBF-1  077 dg frm OK0BAD-2  204km"))
        self.engine._on_frame(ui("OK0BAD-2", "ID", "OK0BAD-2/R WIDE1-1"))
        self.engine._on_frame(ui("OK1AAA", "QST", "net tonight at 20:00"))
        self.engine._on_frame(ui("OK1BBB", MYCALL, "hi, are you there?"))
        texts = [e["text"] for e in self.engine.chat]
        self.assertIn("net tonight at 20:00", texts)
        self.assertIn("hi, are you there?", texts)
        self.assertFalse(any("DX de" in t or "/R WIDE" in t for t in texts))
        self.assertTrue(any("DX de" in line for line in self.engine.monitor))

    async def test_chat_parts(self):
        from aprs_kiss_core.engine import chat_parts
        self.assertEqual(chat_parts("  hello  "), ["hello"])
        self.assertEqual(chat_parts("?anyone there"), [" ?anyone there"])  # not mistaken for APRS
        self.assertEqual(chat_parts(":-)"), [" :-)"])
        long = ("slyšíš mě dobře? " * 40).strip()
        parts = chat_parts(long)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p.encode("utf-8")) <= 256 for p in parts))
        self.assertEqual(" ".join(parts).split(), long.split())  # nothing lost, split between words
        self.assertEqual(chat_parts(""), [])

    async def test_transmit_is_off_by_default(self):
        self.assertFalse(self.engine.tx_enabled)
        with self.assertRaises(TransmitRefused):
            await self.engine.send_aprs_message("OK1ABC-9", "hello")

    async def test_mic_e_beacon(self):
        """Mic-E: the position in the destination address, read back by the parser; EMERGENCY too."""
        import aprslib

        self.engine.set_tx(True)
        sent = []
        real = self.engine.station._send_frame

        async def keep(raw):
            sent.append(raw)
            await real(raw)
        self.engine.station._send_frame = keep
        self.engine.config.mic_e = True
        self.engine.config.mic_e_status = "emergency"
        self.assertTrue(await self.engine.beacon())
        from aprs_kiss_core.ax25 import Frame
        frame = Frame.decode(sent[-1])
        p = aprslib.parse(frame.tnc2())
        self.assertEqual(p["format"], "mic-e")
        self.assertIn("Emergency", p["mtype"])
        self.assertAlmostEqual(p["latitude"], 49.7, places=3)
        self.assertAlmostEqual(p["longitude"], 13.4, places=3)

    async def _capture(self):
        self.engine.set_tx(True)
        sent = []
        real = self.engine.station._send_frame

        async def keep(raw):
            sent.append(raw)
            await real(raw)
        self.engine.station._send_frame = keep
        return sent

    async def test_private_beacon(self):
        """Privacy: the position less exact (spaces for the hidden digits), plain and Mic-E; EMERGENCY exact."""
        import aprslib
        from aprs_kiss_core.ax25 import Frame

        sent = await self._capture()
        self.engine.config.latitude, self.engine.config.longitude = 49.7686, 13.4123
        self.engine.config.position_ambiguity = 2
        self.assertTrue(await self.engine.beacon())
        frame = Frame.decode(sent[-1])
        self.assertIn("4946.  N", frame.info.decode())
        self.assertEqual(aprslib.parse(frame.tnc2())["posambiguity"], 2)
        self.engine.config.mic_e = True
        self.assertTrue(await self.engine.beacon())
        p = aprslib.parse(Frame.decode(sent[-1]).tnc2())
        self.assertEqual(p["posambiguity"], 2)
        self.assertAlmostEqual(p["latitude"], 49.775, places=3)
        self.engine.config.mic_e_status = "emergency"
        self.assertTrue(await self.engine.beacon())
        p = aprslib.parse(Frame.decode(sent[-1]).tnc2())
        self.assertEqual(p.get("posambiguity", 0), 0)
        self.assertAlmostEqual(p["latitude"], 49.7686, places=3)

    async def test_bulletins(self):
        """Ours goes out and repeats; one heard lands on the board, a repeat of it is not new."""
        from aprs_kiss_core.ax25 import Frame

        sent = await self._capture()
        entry = await self.engine.send_bulletin("1", "", "Net tonight 20:00 on 145.500", via="radio", hours=4)
        self.assertEqual(Frame.decode(sent[-1]).info.decode(), ":BLN1     :Net tonight 20:00 on 145.500")
        self.assertEqual(entry["sent"], 1)
        self.assertEqual(await self.engine.bulletin_tick(time.time() + 30), 0)
        self.assertEqual(await self.engine.bulletin_tick(time.time() + 61), 1)
        self.engine.stop_bulletin("BLN1")
        self.assertEqual(self.engine.board.mine, [])
        with self.assertRaises(ValueError):
            await self.engine.send_bulletin("A", "WX", "group needs a digit")
        packet = {"from": "OK1ABC-9", "format": "announcement", "aid": "B", "identifier": "",
                  "message_text": "Hamfest on Saturday", "received_at": time.time()}
        self.engine._bulletin_in(packet, "radio")
        self.engine._bulletin_in(packet, "radio")
        shown = self.engine.bulletins_shown()
        self.assertEqual([(e["addressee"], e["count"]) for e in shown], [("BLNB", 2)])
        self.assertEqual(self.engine.bulletins_unread(), 1)
        self.engine.bulletins_read()
        self.assertEqual(self.engine.bulletins_unread(), 0)
        far = {**packet, "from": "W1AW", "message_text": "far away"}
        self.engine._bulletin_in(far, "internet")  # position unknown, not by radio: off the board
        self.assertEqual(len(self.engine.bulletins_shown()), 1)
        await self.engine.save()
        from aprs_kiss_core.config import load_state
        self.assertEqual(len(load_state(self.folder)["bulletins"]["heard"]), 2)

    async def test_message_is_acked(self):
        self.engine.set_tx(True)
        result = await self.engine.send_aprs_message("OK1ABC-9", "hello", via="radio")
        self.assertTrue(await wait_for(lambda: self.engine.message_state(result["id"]) == "acked"))

    async def test_bbs_session(self):
        self.engine.set_tx(True)
        self.engine.connect("OK0BBS")
        self.assertTrue(await wait_for(lambda: self.engine.session_states().get("OK0BBS") == "connected"))
        self.assertTrue(await wait_for(lambda: any("Welcome" in e["text"] for e in self.engine.terminal)))
        self.engine.send_text("OK0BBS", "H\r")
        self.assertTrue(await wait_for(lambda: any("Commands:" in e["text"] for e in self.engine.terminal)))
        self.engine.disconnect("OK0BBS")
        self.assertTrue(await wait_for(lambda: not self.engine.session_states()))

    async def test_state_is_saved_and_reconfigure_keeps_history(self):
        self.assertTrue(await wait_for(lambda: any(m["direction"] == "in" for m in self.engine.messages)))
        await self.engine.save()
        self.assertTrue(load_state(self.folder)["messages"])
        before = len(self.engine.messages)
        conf = Config.from_dict({**self.engine.config.to_dict(), "comment": "new"}).validate()
        await self.engine.reconfigure(conf)
        self.assertGreaterEqual(len(self.engine.messages), before)
        self.assertEqual(self.engine.station.config.comment, "new")
        self.assertTrue(await wait_for(lambda: self.engine.connection.connected))


class ConfigTest(unittest.TestCase):
    def test_round_trip_and_coercion(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            save_config(Config(callsign="ok1sim-7", path="wide1-1 wide2-1", port=8002).validate(), folder)
            conf = load_config(folder)
            self.assertEqual(conf.callsign, "OK1SIM-7")
            self.assertEqual(conf.path, "WIDE1-1,WIDE2-1")
            self.assertEqual(conf.port, 8002)
        conf = Config.from_dict({"port": "8003", "beacon_is": "true", "latitude": "", "unknown": 1})
        self.assertEqual((conf.port, conf.beacon_is, conf.latitude), (8003, True, None))

    def test_saved_bbs(self):
        conf = Config()
        self.assertEqual(conf.saved_bbs(), [])
        conf.save_bbs("ok0bbs", "ok0abc")
        conf.save_bbs("OK0NOD")
        conf.save_bbs("OK0BBS", "")  # saving again updates the path, keeps one entry
        self.assertEqual(conf.saved_bbs(), [{"call": "OK0NOD", "path": ""}, {"call": "OK0BBS", "path": ""}])
        again = Config.from_dict(conf.to_dict())
        self.assertEqual(again.saved_bbs(), conf.saved_bbs())
        again.remove_bbs("ok0nod")
        self.assertEqual([i["call"] for i in again.saved_bbs()], ["OK0BBS"])
        self.assertEqual(Config(bbs_list="not json").saved_bbs(), [])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            Config(callsign="OK1SIM", symbol="x").validate()
        with self.assertRaises(ValueError):
            Config(latitude=95, longitude=0).validate()

    def test_aprsis_needs_the_licence(self):
        self.assertFalse(Config(aprsis_enabled=True).aprsis_on)
        self.assertTrue(Config(aprsis_enabled=True, licence_confirmed=True).aprsis_on)
        self.assertTrue(Config(aprsis_enabled=False, licence_confirmed=True).validate().licence_confirmed)  # kept


if __name__ == "__main__":
    unittest.main()
