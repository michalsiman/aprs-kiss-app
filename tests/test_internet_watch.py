import asyncio
import time
import types
import unittest

from aprs_kiss_app.app import App


class FakeApp:
    """Just what App._watch_internet uses."""

    INTERNET_EVERY = App.INTERNET_EVERY
    INTERNET_FAILS = App.INTERNET_FAILS
    INTERNET_RETRY = App.INTERNET_RETRY
    RESUME_GRACE = App.RESUME_GRACE
    _foreground = True
    _resumed_at = 0.0
    no_internet = False
    _lifecycle = App._lifecycle
    _checking_paused = App._checking_paused
    _watch_internet = App._watch_internet

    def __init__(self, answers):
        self.answers = list(answers)
        self.changes = []
        self.engine = types.SimpleNamespace(config=types.SimpleNamespace(map_offline=False))
        self.page = types.SimpleNamespace(update=lambda: None)

    def _internet_up(self):
        return self.answers.pop(0) if self.answers else True

    def base_maps_changed(self):
        self.changes.append(self.no_internet)

    def toast(self, *_a, **_k):
        pass

    def t(self, key):
        return key


async def run(app, steps):
    real_sleep = asyncio.sleep
    calls = []

    async def fake_sleep(_seconds):
        calls.append(_seconds)
        if len(calls) > steps:
            raise asyncio.CancelledError
        await real_sleep(0)

    asyncio.sleep = fake_sleep
    try:
        await app._watch_internet()
    except asyncio.CancelledError:
        pass
    finally:
        asyncio.sleep = real_sleep
    return calls


class InternetWatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_one_failed_check_does_not_flip_the_map(self):
        app = FakeApp([True, False, True, False, False, True])
        await run(app, 7)
        self.assertEqual(app.changes, [])

    async def test_three_failures_in_a_row_go_offline_and_back(self):
        app = FakeApp([True, False, False, False, True])
        await run(app, 6)
        self.assertEqual(app.changes, [True, False])

    async def test_no_internet_at_start_is_offline_at_once(self):
        app = FakeApp([False])
        await run(app, 2)
        self.assertEqual(app.changes[:1], [True])

    async def test_background_and_just_resumed_are_not_checked(self):
        app = FakeApp([True, False, False, False, False])
        app._lifecycle(types.SimpleNamespace(state="pause"))
        await run(app, 3)
        self.assertEqual(len(app.answers), 5)  # nothing asked in the background
        app._lifecycle(types.SimpleNamespace(state="resume"))
        self.assertTrue(app._checking_paused())
        app._resumed_at = time.monotonic() - App.RESUME_GRACE - 1
        self.assertFalse(app._checking_paused())


if __name__ == "__main__":
    unittest.main()
