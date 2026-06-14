from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone

from models import Article, title_tokens


HIGH_IMPACT_TERMS = {
    "war", "ceasefire", "election", "government", "court", "ban", "tariff",
    "economy", "inflation", "interest rate", "market", "security", "cyberattack",
    "climate", "earthquake", "outbreak", "regulation", "launch", "breakthrough",
    "funding", "acquisition", "model", "open source", "semiconductor",
}


def _term_hits(text: str, terms: list[str] | set[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def _source_weight(source: str, weights: dict[str, float]) -> float:
    lowered = source.lower()
    for name, weight in weights.items():
        if name.lower() in lowered:
            return float(weight)
    return 1.0


def _learned_adjustment(article: Article, memory: dict) -> tuple[float, list[str]]:
    text = f"{article.title} {article.description}".lower()
    adjustment = 0.0
    reasons = []
    for topic, weight in memory.get("topics", {}).items():
        if topic.lower() in text:
            adjustment += float(weight) * 0.7
            reasons.append(f"learned topic: {topic}")
    for source, weight in memory.get("sources", {}).items():
        if source.lower() in article.source.lower():
            adjustment += float(weight) * 0.8
            reasons.append(f"learned source: {source}")
    return adjustment, reasons


def score_article(article: Article, settings: dict, memory: dict | None = None) -> Article:
    profile = settings["profile"]
    text = f"{article.title} {article.description}"
    priority_hits = _term_hits(text, profile.get("priority_topics", []))
    interest_hits = _term_hits(text, profile.get("interests", []))
    impact_hits = _term_hits(text, HIGH_IMPACT_TERMS)
    avoid_hits = _term_hits(text, profile.get("avoid_topics", []))

    freshness = 4.0 * math.exp(-article.age_hours / 24)
    score = freshness
    score += min(4.0, len(priority_hits) * 1.5)
    score += min(2.5, len(interest_hits) * 0.8)
    score += min(2.5, len(impact_hits) * 0.55)
    score -= len(avoid_hits) * 3.0
    score *= _source_weight(article.source, settings["source_weights"])
    learned_score, learned_reasons = _learned_adjustment(article, memory or {})
    score += learned_score

    reasons = []
    if article.age_hours <= 8:
        reasons.append("very recent")
    if priority_hits:
        reasons.append("priority: " + ", ".join(priority_hits[:2]))
    if impact_hits:
        reasons.append("potentially high impact")
    if _source_weight(article.source, settings["source_weights"]) > 1:
        reasons.append("high-trust source")
    reasons.extend(learned_reasons[:2])

    article.score = round(score, 3)
    article.score_reasons = tuple(reasons)
    return article


def _similar(left: Article, right: Article) -> bool:
    left_tokens = title_tokens(left.title)
    right_tokens = title_tokens(right.title)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= 0.64


def rank_and_dedupe(
    articles: list[Article],
    settings: dict,
    seen_ids: set[str] | None = None,
    memory: dict | None = None,
) -> list[Article]:
    seen_ids = seen_ids or set()
    max_age = float(settings["max_age_hours"])
    candidates = [
        score_article(article, settings, memory)
        for article in articles
        if article.age_hours <= max_age and article.fingerprint not in seen_ids
    ]
    candidates.sort(key=lambda article: article.score, reverse=True)

    selected: list[Article] = []
    for candidate in candidates:
        duplicate = next((item for item in selected if _similar(candidate, item)), None)
        if duplicate:
            sources = list(duplicate.corroborating_sources or (duplicate.source,))
            urls = list(duplicate.corroborating_urls or (duplicate.url,))
            if candidate.source not in sources:
                sources.append(candidate.source)
                urls.append(candidate.url)
            duplicate.corroborating_sources = tuple(sources)
            duplicate.corroborating_urls = tuple(urls)
            duplicate.confidence = "corroborated" if len(sources) >= 2 else "single-source"
            duplicate.score = round(duplicate.score + min(1.5, 0.35 * (len(sources) - 1)), 3)
            duplicate.score_reasons = tuple(
                list(duplicate.score_reasons) + [f"corroborated by {len(sources)} sources"]
            )
            continue
        candidate.corroborating_sources = (candidate.source,)
        candidate.corroborating_urls = (candidate.url,)
        selected.append(candidate)
    return sorted(selected, key=lambda article: article.score, reverse=True)


def select_candidates(articles: list[Article], settings: dict) -> dict[str, list[Article]]:
    limit = int(settings["max_candidates_per_category"])
    grouped: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        grouped[article.category].append(article)
    return {
        category: sorted(items, key=lambda item: item.score, reverse=True)[:limit]
        for category, items in grouped.items()
    }
