import sqlite3
import tempfile
import unittest
import urllib.request
import zipfile
from pathlib import Path

from aprs_kiss_core import tilemaps
from aprs_kiss_core.tilemaps import MapError, import_file, open_source, remove_map, zxy_to_tileid

PNG = b"\x89PNG\r\n\x1a\n" + b"fake"
JPG = b"\xff\xd8\xff\xe0" + b"fake"


def make_mbtiles(path: Path, fmt: str = "png", data: bytes = PNG) -> None:
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE metadata (name text, value text)")
    db.execute("CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)")
    db.executemany("INSERT INTO metadata VALUES (?, ?)",
                   [("name", "Topo"), ("format", fmt), ("bounds", "12,48.5,19,51"), ("attribution", "<a>© Topo</a>")])
    # zoom 8, x 137, XYZ y 87 -> TMS row 255 - 87 = 168
    db.execute("INSERT INTO tiles VALUES (8, 137, 168, ?)", (data,))
    db.execute("INSERT INTO tiles VALUES (12, 2200, 2700, ?)", (data,))
    db.commit()
    db.close()


class TileIdTest(unittest.TestCase):
    def test_pmtiles_spec_values(self):
        self.assertEqual(zxy_to_tileid(0, 0, 0), 0)
        self.assertEqual(zxy_to_tileid(1, 0, 0), 1)
        self.assertEqual(zxy_to_tileid(1, 0, 1), 2)
        self.assertEqual(zxy_to_tileid(1, 1, 1), 3)
        self.assertEqual(zxy_to_tileid(1, 1, 0), 4)
        self.assertEqual(zxy_to_tileid(2, 0, 0), 5)

    def test_ids_are_unique_per_zoom(self):
        for z in range(4):
            ids = {zxy_to_tileid(z, x, y) for x in range(1 << z) for y in range(1 << z)}
            self.assertEqual(len(ids), 4 ** z)
            self.assertEqual(min(ids), (4 ** z - 1) // 3)


def _varints(values):
    out = bytearray()
    for v in values:
        while True:
            b = v & 0x7F
            v >>= 7
            out.append(b | (0x80 if v else 0))
            if not v:
                break
    return bytes(out)


def make_pmtiles(path: Path, tiles: dict, kind: int = 2) -> None:
    """A minimal PMTiles v3 file: one root directory, uncompressed."""
    import struct
    entries = sorted((zxy_to_tileid(*k), v) for k, v in tiles.items())
    blob, offsets = b"", []
    for _, data in entries:
        offsets.append(len(blob))
        blob += data
    ids = [e[0] for e in entries]
    deltas = [ids[0]] + [b - a for a, b in zip(ids, ids[1:])]
    directory = (_varints([len(entries)]) + _varints(deltas) + _varints([1] * len(entries))
                 + _varints([len(d) for _, d in entries]) + _varints([o + 1 for o in offsets]))
    root_off = 127
    data_off = root_off + len(directory)
    head = bytearray(b"PMTiles" + bytes([3]))
    head += struct.pack("<8Q", root_off, len(directory), data_off, 0, data_off, 0, data_off, len(blob))
    head += struct.pack("<3Q", len(entries), len(entries), len(entries))
    head += bytes([0, 1, 1, kind, 8, 12])
    head += struct.pack("<4i", 120000000, 485000000, 190000000, 510000000)
    head += bytes([10]) + struct.pack("<2i", 0, 0)
    assert len(head) == 127
    path.write_bytes(bytes(head) + directory + blob)


class SourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_mbtiles(self):
        make_mbtiles(self.dir / "a.mbtiles")
        src = open_source(self.dir / "a.mbtiles")
        self.assertEqual((src.name, src.fmt, src.min_zoom, src.max_zoom), ("Topo", "png", 8, 12))
        self.assertEqual(src.bounds, (12.0, 48.5, 19.0, 51.0))
        self.assertEqual(src.attribution, "© Topo")
        self.assertEqual(src.tile(8, 137, 87), PNG)
        self.assertIsNone(src.tile(8, 137, 168))
        src.close()

    def test_vector_mbtiles_refused(self):
        make_mbtiles(self.dir / "v.mbtiles", fmt="pbf", data=b"\x1f\x8bxx")
        with self.assertRaises(MapError) as err:
            open_source(self.dir / "v.mbtiles")
        self.assertEqual(err.exception.code, "vector")

    def test_sqlitedb_rmaps(self):
        db = sqlite3.connect(self.dir / "o.sqlitedb")
        db.execute("CREATE TABLE tiles (x int, y int, z int, s int, image blob)")
        db.execute("CREATE TABLE info (maxzoom int, minzoom int)")
        db.execute("INSERT INTO tiles VALUES (137, 87, 9, 0, ?)", (JPG,))  # 17 - 8
        db.commit()
        db.close()
        src = open_source(self.dir / "o.sqlitedb")
        self.assertEqual((src.fmt, src.min_zoom, src.max_zoom), ("jpg", 8, 8))
        self.assertEqual(src.tile(8, 137, 87), JPG)

    def test_pmtiles(self):
        tiles = {(8, 137, 87): PNG, (8, 138, 87): PNG + b"2", (12, 2200, 1395): PNG + b"3"}
        make_pmtiles(self.dir / "p.pmtiles", tiles)
        src = open_source(self.dir / "p.pmtiles")
        self.assertEqual((src.fmt, src.min_zoom, src.max_zoom), ("png", 8, 12))
        self.assertEqual(src.bounds, (12.0, 48.5, 19.0, 51.0))
        for key, data in tiles.items():
            self.assertEqual(src.tile(*key), data)
        self.assertIsNone(src.tile(8, 139, 87))
        src.close()

    def test_zip_and_folder_of_tiles(self):
        with zipfile.ZipFile(self.dir / "t.zip", "w") as z:
            z.writestr("Topo/8/137/87.png", PNG)
            z.writestr("Topo/9/274/175.png", PNG)
        src = open_source(self.dir / "t.zip")
        self.assertEqual((src.min_zoom, src.max_zoom, src.fmt), (8, 9, "png"))
        self.assertEqual(src.tile(9, 274, 175), PNG)
        folder = self.dir / "f" / "8" / "137"
        folder.mkdir(parents=True)
        (folder / "87.jpg").write_bytes(JPG)
        self.assertEqual(open_source(self.dir / "f").tile(8, 137, 87), JPG)

    def test_unknown_file(self):
        (self.dir / "x.txt").write_text("hello")
        with self.assertRaises(MapError):
            open_source(self.dir / "x.txt")


class ImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.maps = self.dir / "maps"

    def tearDown(self):
        self.tmp.cleanup()

    def test_computer_keeps_file_in_place(self):
        make_mbtiles(self.dir / "a.mbtiles")
        self.assertEqual(import_file(self.dir / "a.mbtiles", self.maps, True), [self.dir / "a.mbtiles"])

    def test_phone_moves_the_picked_copy(self):
        make_mbtiles(self.dir / "a.mbtiles")
        [path] = import_file(self.dir / "a.mbtiles", self.maps, False)
        self.assertEqual(path, self.maps / "a.mbtiles")
        self.assertFalse((self.dir / "a.mbtiles").exists())
        remove_map(path, self.maps)
        self.assertFalse(path.exists())

    def test_zip_with_map_files_is_unpacked(self):
        make_mbtiles(self.dir / "a.mbtiles")
        make_pmtiles(self.dir / "b.pmtiles", {(8, 137, 87): PNG})
        with zipfile.ZipFile(self.dir / "pack.zip", "w") as z:
            z.write(self.dir / "a.mbtiles", "maps/a.mbtiles")
            z.write(self.dir / "b.pmtiles", "b.pmtiles")
        found = import_file(self.dir / "pack.zip", self.maps, True)
        self.assertEqual(sorted(p.name for p in found), ["a.mbtiles", "b.pmtiles"])
        self.assertTrue(all(p.parent == self.maps for p in found))

    def test_remove_leaves_outside_files(self):
        make_mbtiles(self.dir / "a.mbtiles")
        remove_map(self.dir / "a.mbtiles", self.maps)
        self.assertTrue((self.dir / "a.mbtiles").exists())

    @unittest.skipUnless(tilemaps._seven_zip(), "no 7-Zip")
    def test_7z(self):
        import subprocess
        make_mbtiles(self.dir / "a.mbtiles")
        subprocess.run([tilemaps._seven_zip(), "a", str(self.dir / "p.7z"), str(self.dir / "a.mbtiles")],
                       capture_output=True, check=True)
        [path] = import_file(self.dir / "p.7z", self.maps, True)
        self.assertEqual(open_source(path).tile(8, 137, 87), PNG)


class ServerTest(unittest.TestCase):
    def test_serves_tiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_mbtiles(Path(tmp) / "a.mbtiles")
            server = tilemaps.TileServer()
            try:
                [(url, src)], failed = server.set_maps([str(Path(tmp) / "a.mbtiles"), str(Path(tmp) / "nope")])
                self.assertEqual(len(failed), 1)
                with urllib.request.urlopen(url.format(z=8, x=137, y=87)) as r:
                    self.assertEqual((r.read(), r.headers["Content-Type"]), (PNG, "image/png"))
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(url.format(z=8, x=1, y=1))
            finally:
                server.close()


if __name__ == "__main__":
    unittest.main()
