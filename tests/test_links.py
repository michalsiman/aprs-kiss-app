import unittest

from aprs_kiss_core.links import split_links


class LinksTest(unittest.TestCase):
    def test_links(self):
        self.assertEqual(split_links("viz https://aprs.fi/OK1SIM, pozdrav"),
                         [("viz ", None), ("https://aprs.fi/OK1SIM", "https://aprs.fi/OK1SIM"), (", pozdrav", None)])
        self.assertEqual(split_links("www.ok1sim.cz."), [("www.ok1sim.cz", "https://www.ok1sim.cz"), (".", None)])
        self.assertEqual(split_links("(http://x.org/a_(b))"),
                         [("(", None), ("http://x.org/a_(b)", "http://x.org/a_(b)"), (")", None)])

    def test_no_links(self):
        self.assertEqual(split_links("73 de OK1SIM, 145.500"), [("73 de OK1SIM, 145.500", None)])
        self.assertEqual(split_links(""), [])
        self.assertEqual(split_links("javascript:alert(1) ftp://x.cz"), [("javascript:alert(1) ftp://x.cz", None)])


if __name__ == "__main__":
    unittest.main()
