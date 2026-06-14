from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from models import Article


SECTION_META = {
    "global": ("Global Intelligence", "The events most likely to shape the wider world."),
    "ai_tech": ("AI & Technology", "Material developments, stripped of launch-day hype."),
    "india": ("India Focus", "Policy, business, society, and events that matter in India."),
}


def _prompt(candidates: dict[str, list[Article]], settings: dict) -> str:
    payload = {
        key: [article.prompt_dict() for article in articles]
        for key, articles in candidates.items()
    }
    profile = settings["profile"]
    count = int(settings["stories_per_category"])
    return f"""
You are the private morning intelligence editor for one reader.

Reader profile:
{json.dumps(profile, ensure_ascii=False, indent=2)}

Learned preferences from explicit reader feedback:
{json.dumps(settings.get("learned_preferences", {}), ensure_ascii=False, indent=2)}

Your job is editorial judgment, not generic summarization. Select at most {count}
stories in each category. Prefer consequential, surprising, decision-useful news.
Reject duplicates, weak speculation, minor product announcements, clickbait, and
stories that do not help this reader understand what changed.

Return ONLY valid JSON with this exact shape:
{{
  "executive_summary": "2-3 sentence synthesis of the morning, connecting themes",
  "attention": "one sentence naming the single thing worth watching today",
  "connections": [
    "up to 3 non-obvious patterns connecting multiple supplied stories"
  ],
  "counterpoint": "one sentence challenging the most tempting overreaction in today's news",
  "sections": {{
    "global": [story],
    "ai_tech": [story],
    "india": [story]
  }}
}}

Each story must be:
{{
  "article_id": "copy the supplied id exactly",
  "headline": "clear factual headline, max 14 words",
  "summary": "what happened and essential context, max 45 words",
  "why_it_matters": "specific relevance or consequence, max 30 words",
  "signal": "HIGH or MEDIUM",
  "watch_next": "one concrete next development to monitor, max 18 words"
}}

Rules:
- Never invent facts, sources, URLs, motives, numbers, or implications.
- Use only supplied articles and preserve article_id exactly.
- When reports conflict, say so.
- Treat corroborated stories as more reliable, but do not confuse repetition with truth.
- Connections must be grounded in at least two supplied stories.
- Avoid breathless language and empty phrases.
- A shorter section is better than padding it with weak news.

Candidates:
{json.dumps(payload, ensure_ascii=False)}
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.rsplit("```", 1)[0]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Gemini did not return a JSON object")
    return json.loads(cleaned[start : end + 1])


def _fallback(candidates: dict[str, list[Article]], settings: dict) -> dict:
    count = int(settings["stories_per_category"])
    sections = {}
    for category in SECTION_META:
        sections[category] = [
            {
                "article_id": article.fingerprint,
                "headline": article.title,
                "summary": article.description or "Open the source for full details.",
                "why_it_matters": "Selected for recency, relevance, and likely impact.",
                "signal": "HIGH" if article.score >= 7 else "MEDIUM",
                "watch_next": "Watch for confirmed follow-up reporting.",
            }
            for article in candidates.get(category, [])[:count]
        ]
    return {
        "executive_summary": "Here are the highest-ranked developments from the latest reporting.",
        "attention": "Open the linked sources for any story affecting a decision today.",
        "connections": [],
        "counterpoint": "A prominent headline is not automatically the most consequential story.",
        "sections": sections,
    }


def summarize(candidates: dict[str, list[Article]], settings: dict) -> dict:
    if not any(candidates.values()):
        return {
            "executive_summary": "No sufficiently recent, unseen stories were found.",
            "attention": "The agent will check again at the next scheduled run.",
            "connections": [],
            "counterpoint": "Silence in the feed is not evidence that nothing important changed.",
            "sections": {key: [] for key in SECTION_META},
        }

    if not settings.get("gemini_api_key"):
        print("Warning: GEMINI_API_KEY is missing; using ranked fallback")
        return _fallback(candidates, settings)

    try:
        from google import genai

        client = genai.Client(api_key=settings["gemini_api_key"])
        response = client.models.generate_content(
            model=settings["model"],
            contents=_prompt(candidates, settings),
            config={"response_mime_type": "application/json", "temperature": 0.2},
        )
        digest = _extract_json(response.text)
        digest.setdefault("sections", {})
        for key in SECTION_META:
            digest["sections"].setdefault(key, [])
        return digest
    except Exception as exc:
        print(f"Warning: AI editorial pass failed; using ranked fallback: {exc}")
        return _fallback(candidates, settings)


def hydrate_digest(
    digest: dict,
    candidates: dict[str, list[Article]],
) -> tuple[dict, list[Article]]:
    lookup = {
        article.fingerprint: article
        for articles in candidates.values()
        for article in articles
    }
    used: list[Article] = []
    for category, stories in digest.get("sections", {}).items():
        hydrated = []
        for story in stories:
            article = lookup.get(story.get("article_id", ""))
            if not article:
                continue
            story["url"] = article.url
            story["source"] = article.source
            story["published_at"] = article.published_at.isoformat()
            story["confidence"] = article.confidence
            story["evidence_sources"] = list(article.corroborating_sources)
            story["evidence_urls"] = list(article.corroborating_urls)
            hydrated.append(story)
            used.append(article)
        digest["sections"][category] = hydrated
    return digest, used
