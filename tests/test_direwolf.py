import asyncio
import os
import pathlib
import stat
import sys
import tempfile
import textwrap
import unittest

from aprs_kiss_core import direwolf
from aprs_kiss_core.connection import TncSettings

FAKE = textwrap.dedent('''\
    #!{python}
    import asyncio, re, sys
    conf = open(sys.argv[sys.argv.index("-c") + 1]).read()
    port = int(re.search(r"KISSPORT (\\d+)", conf).group(1))
    print("Dire Wolf fake, listening on", port, flush=True)
    async def main():
        server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", port)
        await asyncio.sleep(3600)
    asyncio.run(main())
''')


class DirewolfTest(unittest.IsolatedAsyncioTestCase):
    def test_config(self):
        text = direwolf.make_config("OK1SIM-7", "plughw:1,0", "CM108", 8101)
        self.assertIn("ADEVICE plughw:1,0", text)
        self.assertIn("MYCALL OK1SIM-7", text)
        self.assertIn("PTT CM108", text)
        self.assertIn("KISSPORT 8101", text)
        self.assertIn("AGWPORT 0", text)
        self.assertIn("PTT /dev/ttyUSB0 RTS", direwolf.make_config("X", "", "RTS:/dev/ttyUSB0", 8101))
        vox = direwolf.make_config("X", "", "", 8101)
        self.assertNotIn("PTT", vox)
        self.assertNotIn("ADEVICE", vox)  # the system's default sound card

    @unittest.skipIf(sys.platform == "win32", "a shell script as the fake Direwolf")
    async def test_start_connect_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            fake = folder / "direwolf"
            fake.write_text(FAKE.format(python=sys.executable))
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            modem = direwolf.MODEM
            port = 18000 + os.getpid() % 1000
            modem.configure(str(fake), direwolf.make_config("OK1SIM", "", "", port), folder)
            reader, writer = await direwolf._open(TncSettings(kind="direwolf", port=port))
            self.assertTrue(modem.running)
            self.assertTrue((folder / direwolf.CONFIG_NAME).exists())
            writer.close()
            await modem.stop()
            self.assertFalse(modem.running)
            self.assertTrue(any("listening" in line for line in modem.log))

    async def test_not_installed(self):
        direwolf.MODEM.configure("", "", pathlib.Path(tempfile.gettempdir()))
        with self.assertRaises(OSError):
            await direwolf._open(TncSettings(kind="direwolf", port=1))


if __name__ == "__main__":
    unittest.main()
