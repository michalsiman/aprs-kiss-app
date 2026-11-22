"""VARA FM: the client against a pretend VARA, and the terminal going through it."""

import asyncio
import pathlib
import socket
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aprs_kiss_core import vara  # noqa: E402
from aprs_kiss_core.config import Config  # noqa: E402
from aprs_kiss_core.engine import Engine  # noqa: E402

from tests.fake_vara import FakeVara, serve  # noqa: E402


def free_port() -> int:
    """Two free ports in a row (VARA's data port is the command port + 1)."""
    for _ in range(50):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        with socket.socket() as a, socket.socket() as b:
            try:
                a.bind(("127.0.0.1", port))
                b.bind(("127.0.0.1", port + 1))
                return port
            except OSError:
                continue
    raise RuntimeError("no free ports")


async def wait_for(check, timeout=5.0):
    for _ in range(int(timeout / 0.02)):
        if check():
            return True
        await asyncio.sleep(0.02)
    return False


class VaraClientTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeVara(delay=0.05)
        self.port = free_port()
        self.servers = await serve(self.port, self.fake)
        self.states, self.text = [], []
        self.client = vara.VaraClient("127.0.0.1", self.port, "OK1SIM-7",
                                      lambda s, r: self.states.append((s, r)), self.text.append)
        await self.client.start()
        self.assertTrue(await wait_for(lambda: self.client.link_up))

    async def asyncTearDown(self):
        await self.client.stop()
        for s in self.servers:
            s.close()

    async def test_session(self):
        self.assertTrue(await wait_for(lambda: "LISTEN OFF" in self.fake.commands))
        self.assertIn("MYCALL OK1SIM-7", self.fake.commands)
        await self.client.connect("OK0BBS", ["OK0DIG"])
        self.assertTrue(await wait_for(lambda: "CONNECT OK1SIM-7 OK0BBS via OK0DIG" in self.fake.commands))
        self.assertTrue(await wait_for(lambda: self.client.state == vara.CONNECTED))
        self.assertTrue(await wait_for(lambda: "Welcome OK1SIM-7" in "".join(self.text)))
        await self.client.send("L\n")
        self.assertTrue(await wait_for(lambda: "Test bulletin over VARA" in "".join(self.text)))
        self.assertTrue(await wait_for(lambda: self.fake.received == b"L\r"))
        await self.client.disconnect()
        self.assertTrue(await wait_for(lambda: self.client.state == vara.IDLE))
        self.assertEqual(self.states[-1], (vara.IDLE, "disconnected"))

    async def test_no_answer_and_abort(self):
        await self.client.connect("NOANSWER")
        self.assertTrue(await wait_for(lambda: self.client.state == vara.IDLE))
        self.assertIn("no answer", [r for _, r in self.states])
        await self.client.connect("OK0BBS")
        await self.client.disconnect()  # still connecting: stop at once
        self.assertTrue(await wait_for(lambda: "ABORT" in self.fake.commands))
        self.assertEqual(self.client.state, vara.IDLE)

    async def test_vara_not_running(self):
        lonely = vara.VaraClient("127.0.0.1", free_port(), "OK1SIM", lambda s, r: None, lambda t: None)
        with self.assertRaises(ConnectionError):
            await lonely.connect("OK0BBS")


class EngineVaraTest(unittest.IsolatedAsyncioTestCase):
    async def test_terminal_over_vara(self):
        fake = FakeVara(delay=0.05)
        port = free_port()
        servers = await serve(port, fake)
        with tempfile.TemporaryDirectory() as tmp:
            eng = Engine(Config(callsign="OK1SIM-7", host="127.0.0.1", port=1, vara_host="127.0.0.1",
                                vara_port=port).validate(), pathlib.Path(tmp))
            await eng.start()
            try:
                self.assertTrue(await wait_for(lambda: eng.vara.link_up))
                eng.set_tx(True)
                eng.connect("OK0BBS", via="vara")
                self.assertTrue(await wait_for(lambda: eng.session_states().get("OK0BBS") == "connected"))
                self.assertEqual(eng.session_info("OK0BBS")["via"], "vara")
                self.assertTrue(await wait_for(lambda: any("Welcome" in e["text"] for e in eng.terminal)))
                eng.send_text("OK0BBS", "L\n")
                self.assertTrue(await wait_for(lambda: any("Net tonight" in e["text"] for e in eng.terminal)))
                eng.disconnect("OK0BBS")
                self.assertTrue(await wait_for(lambda: "OK0BBS" not in eng.session_states()))
                self.assertTrue(any(e["text"].startswith("VARA: ") for e in eng.terminal))
            finally:
                await eng.stop()
                for s in servers:
                    s.close()

    async def test_vara_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            eng = Engine(Config(callsign="OK1SIM-7").validate(), pathlib.Path(tmp))
            eng.set_tx(True)
            with self.assertRaises(ConnectionError):
                eng.connect("OK0BBS", via="vara")


if __name__ == "__main__":
    unittest.main()
