import unittest

from fetcher import _clean


class FetcherTests(unittest.TestCase):
    def test_clean_removes_html_and_invisible_formatting(self):
        self.assertEqual(
            _clean("<b>Important</b>\u200b&nbsp; news"),
            "Important news",
        )


if __name__ == "__main__":
    unittest.main()
