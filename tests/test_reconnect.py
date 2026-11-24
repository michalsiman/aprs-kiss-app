import asyncio
import unittest
from unittest import mock

from aprs_kiss_core import connection
from aprs_kiss_core.connection import KissConnection, TncSettings


class ReconnectTest(unittest.IsolatedAsyncioTestCase):
    async def test_a_local_tnc_is_looked_for_often_and_at_once_on_request(self):
        tries = []

        async def missing(_settings):
            tries.append(asyncio.get_running_loop().time())
            raise OSError("No USB TNC plugged in")

        connection.register_transport("usb", missing)
        conn = KissConnection(TncSettings(kind="usb", host="", port=0, device="", baudrate=9600), lambda f: None)
        with mock.patch.object(connection, "RECONNECT_MIN", 0.05), mock.patch.object(connection, "RECONNECT_LOCAL", 0.1):
            await conn.start()
            await asyncio.sleep(0.6)
            self.assertGreaterEqual(len(tries), 4)  # not doubling to a minute
            before = len(tries)
        with mock.patch.object(connection, "RECONNECT_LOCAL", 30):
            await asyncio.sleep(0.15)  # now waiting 30 s…
            conn.retry_now()  # …but the app came back to the screen
            await asyncio.sleep(0.1)
            self.assertGreater(len(tries), before)
        await conn.stop()


if __name__ == "__main__":
    unittest.main()
