import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from aprs_kiss_core.config import Config
from aprs_kiss_core.engine import Engine


def station(call, folder, **conf):
    eng = Engine(Config(callsign=call, **conf), Path(folder))
    eng.station.tx_enabled = True
    eng.connection.connected = True
    return eng


class FilesOverTheAirTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_a_file_between_two_stations(self):
        with tempfile.TemporaryDirectory() as a_dir, tempfile.TemporaryDirectory() as b_dir:
            a = station("OK1AAA", a_dir)
            b = station("OK1BBB", b_dir, files_accept=True)
            b._build(tx_enabled=True)  # accept incoming connections (files)
            b.connection.connected = True

            async def a_to_b(raw):
                b._on_frame(raw)

            async def b_to_a(raw):
                a._on_frame(raw)

            a.send_frame, b.send_frame = a_to_b, b_to_a
            offers = []
            b.add_listener(lambda kind, d: offers.append(d) if kind == "file_offer" else None)
            data = os.urandom(5000)
            a.send_file("OK1BBB", "picture.jpg", data)
            for _ in range(4000):
                await asyncio.sleep(0.01)
                if offers and "OK1AAA" in b._offers:
                    b.answer_file("OK1AAA", True)
                if a.transfers and a.transfers[-1]["state"] == "done":
                    break
            self.assertEqual(offers[0]["name"], "picture.jpg")
            self.assertEqual(a.transfers[-1]["state"], "done")
            self.assertEqual(b.transfers[-1]["state"], "done")
            self.assertEqual((Path(b_dir) / "files" / "picture.jpg").read_bytes(), data)
            for eng in (a, b):
                for s in eng.sessions.values():
                    s.close()


if __name__ == "__main__":
    unittest.main()
