from datetime import datetime, timedelta, timezone
import unittest

from models import Article, canonical_url
from ranking import rank_and_dedupe


SETTINGS = {
    "max_age_hours": 48,
    "profile": {
        "priority_topics": ["AI agents"],
        "interests": ["artificial intelligence"],
        "avoid_topics": ["celebrity gossip"],
    },
    "source_weights": {"Reuters": 1.25},
}


def article(title: str, url: str, source: str = "Example") -> Article:
    return Article(
        title=title,
        description="AI agents and artificial intelligence policy update",
        url=url,
        source=source,
        published_at=datetime.now(timezone.utc) - timedelta(hours=2),
        category="ai_tech",
    )


class RankingTests(unittest.TestCase):
    def test_tracking_parameters_are_removed(self):
        self.assertEqual(
            canonical_url("https://example.com/story?utm_source=x&id=2#top"),
            "https://example.com/story?id=2",
        )

    def test_similar_headlines_are_deduplicated(self):
        results = rank_and_dedupe(
            [
                article("OpenAI launches a new AI agent platform", "https://a.com/1"),
                article("OpenAI launches new AI agents platform today", "https://b.com/2"),
            ],
            SETTINGS,
        )
        self.assertEqual(len(results), 1)

    def test_seen_story_is_excluded(self):
        item = article("Important AI agents policy changes", "https://example.com/a")
        results = rank_and_dedupe([item], SETTINGS, {item.fingerprint})
        self.assertEqual(results, [])

    def test_trusted_source_receives_higher_score(self):
        trusted = article("AI agents reshape enterprise software", "https://r.com/a", "Reuters")
        other = article("AI agents reshape business workflows", "https://e.com/a")
        results = rank_and_dedupe([other, trusted], SETTINGS)
        self.assertEqual(results[0].source, "Reuters")

    def test_learned_topic_changes_ranking(self):
        favored = article("Quantum computing reaches a milestone", "https://q.com/a")
        favored.description = "A quantum computing research result"
        ordinary = article("Enterprise software receives an update", "https://s.com/a")
        ordinary.description = "A routine enterprise software maintenance release"
        results = rank_and_dedupe(
            [ordinary, favored],
            SETTINGS,
            memory={"topics": {"quantum computing": 4}, "sources": {}},
        )
        self.assertEqual(results[0].url, favored.url)

    def test_duplicate_sources_create_corroboration(self):
        results = rank_and_dedupe(
            [
                article("OpenAI launches a new AI agent platform", "https://a.com/1", "One"),
                article("OpenAI launches new AI agents platform today", "https://b.com/2", "Two"),
            ],
            SETTINGS,
        )
        self.assertEqual(results[0].confidence, "corroborated")
        self.assertEqual(len(results[0].corroborating_sources), 2)


if __name__ == "__main__":
    unittest.main()
