import io
import unittest
import zipfile

try:
    from PIL import Image
except ImportError:  # the core's CI has no Pillow
    raise unittest.SkipTest("Pillow is not installed")

from aprs_kiss_app import shrink


def photo(w=3000, h=2000):
    img = Image.effect_noise((w, h), 60).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    return buf.getvalue()


class ShrinkTest(unittest.TestCase):
    def test_picture_variants_get_smaller(self):
        data = photo()
        variants = shrink.picture_variants("IMG_0001.jpg", data)
        self.assertEqual(variants[0].key, "original")
        sizes = [len(v.data) for v in variants]
        self.assertEqual(sizes, sorted(sizes, reverse=True))
        self.assertIn("480", [v.key for v in variants])
        v480 = next(v for v in variants if v.key == "480")
        self.assertEqual(max(v480.width, v480.height), 480)
        self.assertEqual(v480.name, "IMG_0001_480.jpg")
        self.assertTrue(variants[-1].grey)

    def test_small_picture_is_not_made_bigger(self):
        variants = shrink.picture_variants("tiny.jpg", photo(200, 100))
        self.assertTrue(all(max(v.width, v.height) <= 200 for v in variants))

    def test_not_a_picture(self):
        self.assertEqual(shrink.picture_variants("a.txt", b"hello"), [])
        self.assertFalse(shrink.is_picture(b"hello"))

    def test_zip(self):
        text = ("CQ CQ de OK1SIM " * 500).encode()
        z = shrink.zipped("log.txt", text)
        self.assertEqual(z.name, "log.txt.zip")
        self.assertLess(len(z.data), len(text) / 5)
        with zipfile.ZipFile(io.BytesIO(z.data)) as f:
            self.assertEqual(f.read("log.txt"), text)
        self.assertIsNone(shrink.zipped("photo.jpg", photo(300, 300)))  # a JPEG hardly packs


if __name__ == "__main__":
    unittest.main()
