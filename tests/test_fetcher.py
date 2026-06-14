import unittest
from unittest.mock import patch

from fetcher import _clean, _normalize_image_url, validate_article_images
from models import Article
from datetime import datetime, timezone


class FetcherTests(unittest.TestCase):
    def test_clean_removes_html_and_invisible_formatting(self):
        self.assertEqual(
            _clean("<b>Important</b>\u200b&nbsp; news"),
            "Important news",
        )

    def test_broken_article_image_is_removed(self):
        item = Article(
            title="Story",
            description="Summary",
            url="https://example.com/story",
            source="BBC",
            published_at=datetime.now(timezone.utc),
            category="global",
            image_url="https://example.com/broken.jpg",
        )
        with patch("fetcher._image_is_available", return_value=False):
            validate_article_images([item])
        self.assertEqual(item.image_url, "")

    def test_hotlink_blocked_image_uses_fallback(self):
        self.assertEqual(
            _normalize_image_url("https://c.ndtvimg.com/photo.jpeg"),
            "",
        )

    def test_bbc_thumbnail_is_upgraded(self):
        self.assertIn(
            "/standard/1024/",
            _normalize_image_url(
                "https://ichef.bbci.co.uk/ace/standard/240/cpsprodpb/photo.jpg"
            ),
        )


if __name__ == "__main__":
    unittest.main()
