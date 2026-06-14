from datetime import timedelta
from unittest.mock import patch
import unittest

from zoneinfo import ZoneInfoNotFoundError

from timeutils import resolve_timezone


class TimezoneTests(unittest.TestCase):
    def test_kolkata_has_builtin_fallback_without_tzdata(self):
        with patch("timeutils.ZoneInfo", side_effect=ZoneInfoNotFoundError):
            tz = resolve_timezone("Asia/Kolkata")
        self.assertEqual(tz.utcoffset(None), timedelta(hours=5, minutes=30))
        self.assertEqual(tz.tzname(None), "IST")

    def test_unknown_zone_falls_back_instead_of_crashing(self):
        with patch("timeutils.ZoneInfo", side_effect=ZoneInfoNotFoundError):
            with self.assertWarns(RuntimeWarning):
                tz = resolve_timezone("Mars/Olympus")
        self.assertIsNotNone(tz)


if __name__ == "__main__":
    unittest.main()
