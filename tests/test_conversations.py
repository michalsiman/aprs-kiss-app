import tempfile
import unittest
from pathlib import Path

from aprs_kiss_core.config import Config
from aprs_kiss_core.engine import Engine


class ConversationTest(unittest.IsolatedAsyncioTestCase):
    async def test_delete_and_distance(self):
        with tempfile.TemporaryDirectory() as tmp:
            eng = Engine(Config(callsign="OK1SIM-7", latitude=50.0, longitude=14.0), Path(tmp))
            eng.station.heard["OK1ABC-9"] = {"call": "OK1ABC-9", "latitude": 50.0, "longitude": 14.14, "last_heard": 0}
            self.assertAlmostEqual(eng._distance_to("OK1ABC-9")["km"], 10.0, delta=0.2)
            self.assertEqual(eng._distance_to("OK1ABC-9")["bearing"], 90)
            self.assertEqual(eng._distance_to("OK1XYZ"), {})
            eng.messages.extend([
                {"direction": "in", "from": "OK1ABC-9", "to": "OK1SIM-7", "text": "a", "time": 1},
                {"direction": "out", "from": "OK1SIM-7", "to": "ok1abc-9", "text": "b", "time": 2},
                {"direction": "in", "from": "OK1XYZ", "to": "OK1SIM-7", "text": "c", "time": 3},
            ])
            self.assertEqual(eng.delete_conversation("OK1ABC-9"), 2)
            self.assertEqual([m["text"] for m in eng.messages], ["c"])
            if eng._save_handle:
                eng._save_handle.cancel()


if __name__ == "__main__":
    unittest.main()
