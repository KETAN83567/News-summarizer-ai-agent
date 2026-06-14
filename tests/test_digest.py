from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from models import Article
from sender import render_html, render_text, save_preview
from summarizer import hydrate_digest


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.article = Article(
            title="A consequential technology story",
            description="Useful context.",
            url="https://example.com/story",
            source="Example News",
            published_at=datetime.now(timezone.utc),
            category="ai_tech",
            image_url="https://example.com/story.jpg",
        )
        self.digest = {
            "executive_summary": "A concise synthesis.",
            "attention": "Watch the policy response.",
            "sections": {
                "global": [],
                "india": [],
                "ai_tech": [
                    {
                        "article_id": self.article.fingerprint,
                        "headline": "Technology policy changes",
                        "summary": "A factual summary.",
                        "why_it_matters": "It changes near-term decisions.",
                        "signal": "HIGH",
                        "watch_next": "The regulator's next announcement.",
                    }
                ],
            },
        }
        self.settings = {
            "timezone": "Asia/Kolkata",
            "profile": {"name": "Reader"},
        }

    def test_hydration_uses_known_source_and_url(self):
        hydrated, used = hydrate_digest(
            self.digest,
            {"global": [], "india": [], "ai_tech": [self.article]},
        )
        story = hydrated["sections"]["ai_tech"][0]
        self.assertEqual(story["url"], self.article.url)
        self.assertEqual(story["source"], self.article.source)
        self.assertEqual(used, [self.article])

    def test_renderers_include_source_link(self):
        hydrated, _ = hydrate_digest(
            self.digest,
            {"global": [], "india": [], "ai_tech": [self.article]},
        )
        self.assertIn(self.article.url, render_text(hydrated))
        rendered = render_html(hydrated, self.settings)
        self.assertIn(self.article.url, rendered)
        self.assertIn(self.article.image_url, rendered)
        self.assertIn("THE DAILY SIGNAL", rendered)
        self.assertIn('class="desktop-feed"', rendered)
        self.assertIn('class="mobile-feed"', rendered)
        self.assertIn("@media only screen and (max-width:600px)", rendered)

    def test_preview_is_written(self):
        hydrated, _ = hydrate_digest(
            self.digest,
            {"global": [], "india": [], "ai_tech": [self.article]},
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "preview.html"
            save_preview(hydrated, self.settings, path)
            self.assertTrue(path.exists())
            self.assertIn("THE DAILY SIGNAL", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
