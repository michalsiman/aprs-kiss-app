import os
import tempfile
import unittest
from pathlib import Path

from aprs_kiss_core import yapp


class Pipe:
    """The two ends wired back to back; bytes are delivered in odd-sized pieces like a real link."""

    def __init__(self, folder, accept=True, data=b""):
        self.states_s, self.states_r, self.progress = [], [], []
        self.sender = yapp.Sender("photo.jpg", data, self.to_r, lambda s, d: self.states_s.append(s))
        self.receiver = yapp.Receiver(Path(folder), self.to_s, lambda n, sz, ans: ans(accept),
                                      lambda s, d: self.states_r.append(s), lambda g, sz: self.progress.append(g))

    def to_r(self, data):
        for i in range(0, len(data), 7):
            self.receiver.feed(data[i:i + 7])

    def to_s(self, data):
        self.sender.feed(data)


class YappTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_whole_file(self):
        data = os.urandom(3000)
        p = Pipe(self.dir, data=data)
        p.sender.start()
        self.assertEqual(p.states_s[-1], "done")
        self.assertEqual(p.states_r[-1], "done")
        self.assertEqual((self.dir / "photo.jpg").read_bytes(), data)
        self.assertEqual(p.progress[-1], 3000)

    def test_refused(self):
        p = Pipe(self.dir, accept=False, data=b"x" * 100)
        p.sender.start()
        self.assertEqual(p.states_s[-1], "refused")
        self.assertFalse(any(self.dir.iterdir()))

    def test_resume_after_an_interrupted_transfer(self):
        data = os.urandom(2000)
        (self.dir / "photo.jpg.part").write_bytes(data[:750])
        p = Pipe(self.dir, data=data)
        p.sender.start()
        self.assertEqual(p.sender.offset, 750)
        self.assertEqual((self.dir / "photo.jpg").read_bytes(), data)

    def test_a_name_that_exists_gets_a_number(self):
        (self.dir / "photo.jpg").write_bytes(b"old")
        Pipe(self.dir, data=b"new").sender.start()
        self.assertEqual((self.dir / "photo-2.jpg").read_bytes(), b"new")

    def test_cancel_and_safe_names(self):
        p = Pipe(self.dir, data=b"x" * 10)
        p.sender.state = "waiting"
        p.sender.cancel("no time")
        self.assertEqual(p.states_r[-1], "cancelled")
        self.assertEqual(yapp.safe_name("../../etc/passwd"), "passwd")
        self.assertEqual(yapp.safe_name(".."), "file")

    def test_parser_joins_and_splits(self):
        parser = yapp.Parser()
        packets = yapp.SI + yapp.header("a.txt", 5) + yapp.data_packets(b"hello")[0] + yapp.EF
        out = parser.feed(packets[:3]) + parser.feed(packets[3:])
        self.assertEqual([k for k, _ in out], [yapp.ENQ, yapp.SOH, yapp.STX, yapp.ETX])
        self.assertEqual(out[2][1], b"hello")


if __name__ == "__main__":
    unittest.main()
