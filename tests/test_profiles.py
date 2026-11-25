import unittest

from aprs_kiss_core import profiles
from aprs_kiss_core.config import Config


class ProfilesTest(unittest.TestCase):
    def test_without_profiles_nothing_changes(self):
        conf = Config(callsign="OK1SIM-15", symbol="/[").validate()
        self.assertEqual((conf.callsign, conf.symbol, conf.profiles), ("OK1SIM-15", "/[", ""))
        self.assertEqual(profiles.load(conf), [{"ssid": 15, "symbol": "/["}])

    def test_switch_changes_callsign_and_symbol(self):
        conf = Config(callsign="OK1SIM-15", symbol="/[",
                      profiles=profiles.dump([{"ssid": 15, "symbol": "/["}, {"ssid": 9, "symbol": "/>"},
                                              {"ssid": 0, "symbol": "/-"}])).validate()
        car = profiles.switch(conf, 1)
        self.assertEqual((car.callsign, car.symbol, car.profile), ("OK1SIM-9", "/>", 1))
        home = profiles.switch(car, 2)
        self.assertEqual((home.callsign, home.symbol), ("OK1SIM", "/-"))
        self.assertEqual(conf.callsign, "OK1SIM-15")  # a copy: the old settings stay as they were
        with self.assertRaises(ValueError):
            profiles.switch(conf, 3)

    def test_saved_settings_follow_the_active_profile(self):
        data = Config(callsign="OK1SIM-7", symbol="/[", profile=1,
                      profiles='[{"ssid": 7, "symbol": "/["}, {"ssid": 9, "symbol": "/>"}]').to_dict()
        conf = Config.from_dict(data).validate()
        self.assertEqual((conf.callsign, conf.symbol), ("OK1SIM-9", "/>"))

    def test_bad_entries_and_duplicates_dropped(self):
        conf = Config(callsign="OK1SIM", profile=5,
                      profiles='[{"ssid": 9, "symbol": "/>"}, {"ssid": 9, "symbol": "/["}, {"ssid": 99}, "x"]')
        conf.validate()
        self.assertEqual(profiles.load(conf), [{"ssid": 9, "symbol": "/>", "comment": "", "tracker_mode": "fixed",
                                                "tracker_minutes": 2, "tracker_profile": "car"}])
        self.assertEqual((conf.profile, conf.callsign), (0, "OK1SIM-9"))

    def test_each_profile_has_its_own_comment(self):
        conf = Config(callsign="OK1SIM-9", comment="old", profiles=profiles.dump([
            {"ssid": 9, "symbol": "/>", "comment": "v autě"}, {"ssid": 7, "symbol": "/[", "comment": "op. Michal"},
            {"ssid": 0, "symbol": "/-"}])).validate()
        self.assertEqual(conf.comment, "v autě")
        self.assertEqual(profiles.switch(conf, 1).comment, "op. Michal")
        self.assertEqual(profiles.switch(conf, 2).comment, "old")  # none of its own: the comment used before

    def test_each_profile_has_its_own_tracker_way(self):
        conf = Config(callsign="OK1SIM-9", tracker_still_minutes=30, profiles=profiles.dump([
            {"ssid": 9, "symbol": "/>", "tracker_mode": "smart", "tracker_profile": "car"},
            {"ssid": 7, "symbol": "/[", "tracker_mode": "fixed", "tracker_minutes": 5}])).validate()
        self.assertEqual((conf.tracker_mode, conf.tracker_profile), ("smart", "car"))
        walk = profiles.switch(conf, 1)
        self.assertEqual((walk.tracker_mode, walk.tracker_minutes), ("fixed", 5))
        self.assertEqual(walk.tracker_still_minutes, 30)  # one for all profiles


if __name__ == "__main__":
    unittest.main()
