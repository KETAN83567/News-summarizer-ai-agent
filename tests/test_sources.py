from datetime import datetime, timezone
import unittest

from config import DEFAULTS
from fetcher import filter_trusted_sources, trusted_source_name
from models import Article


def article(source: str) -> Article:
    return Article(
        title="A consequential report",
        description="Useful context",
        url="https://example.com/story",
        source=source,
        published_at=datetime.now(timezone.utc),
        category="global",
    )


class TrustedSourceTests(unittest.TestCase):
    def test_recognizes_name_alias_and_domain(self):
        self.assertEqual(trusted_source_name("BBC News", DEFAULTS), "BBC")
        self.assertEqual(trusted_source_name("bbc.com", DEFAULTS), "BBC")
        self.assertEqual(trusted_source_name("Livemint", DEFAULTS), "Mint")

    def test_unknown_source_is_rejected_in_strict_mode(self):
        kept = filter_trusted_sources(
            [article("Reuters"), article("Tiny Viral Blog")],
            DEFAULTS,
        )
        self.assertEqual([item.source for item in kept], ["Reuters"])

    def test_strict_mode_can_be_disabled(self):
        settings = dict(DEFAULTS)
        settings["source_policy"] = {"strict": False}
        kept = filter_trusted_sources([article("Tiny Viral Blog")], settings)
        self.assertEqual(len(kept), 1)


if __name__ == "__main__":
    unittest.main()
