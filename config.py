from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.json"

DEFAULTS = {
    "timezone": "Asia/Kolkata",
    "delivery_time": "07:00",
    "recipient": "",
    "model": "gemini-3.5-flash",
    "max_candidates_per_category": 14,
    "stories_per_category": 5,
    "max_age_hours": 48,
    "source_policy": {
        "strict": True,
        "minimum_tier": 2,
        "sources": {
            "Reuters": {
                "tier": 1,
                "aliases": ["Reuters", "reuters.com"],
            },
            "Associated Press": {
                "tier": 1,
                "aliases": ["Associated Press", "AP News", "apnews.com"],
            },
            "BBC": {
                "tier": 1,
                "aliases": ["BBC", "BBC News", "bbc.com", "bbc.co.uk"],
            },
            "Financial Times": {
                "tier": 1,
                "aliases": ["Financial Times", "FT", "ft.com"],
            },
            "Bloomberg": {
                "tier": 1,
                "aliases": ["Bloomberg", "bloomberg.com"],
            },
            "The Guardian": {
                "tier": 2,
                "aliases": ["The Guardian", "Guardian", "theguardian.com"],
            },
            "The New York Times": {
                "tier": 2,
                "aliases": ["The New York Times", "New York Times", "nytimes.com"],
            },
            "The Wall Street Journal": {
                "tier": 2,
                "aliases": ["The Wall Street Journal", "Wall Street Journal", "WSJ", "wsj.com"],
            },
            "CNN": {
                "tier": 2,
                "aliases": ["CNN", "cnn.com"],
            },
            "NPR": {
                "tier": 2,
                "aliases": ["NPR", "npr.org"],
            },
            "Al Jazeera": {
                "tier": 2,
                "aliases": ["Al Jazeera", "aljazeera.com"],
            },
            "Deutsche Welle": {
                "tier": 2,
                "aliases": ["Deutsche Welle", "DW", "dw.com"],
            },
            "The Hindu": {
                "tier": 1,
                "aliases": ["The Hindu", "thehindu.com"],
            },
            "The Indian Express": {
                "tier": 1,
                "aliases": ["The Indian Express", "Indian Express", "indianexpress.com"],
            },
            "Press Trust of India": {
                "tier": 1,
                "aliases": ["Press Trust of India", "PTI"],
            },
            "NDTV": {
                "tier": 2,
                "aliases": ["NDTV", "ndtv.com"],
            },
            "Hindustan Times": {
                "tier": 2,
                "aliases": ["Hindustan Times", "hindustantimes.com"],
            },
            "Mint": {
                "tier": 2,
                "aliases": ["Mint", "Livemint", "livemint.com"],
            },
            "Business Standard": {
                "tier": 2,
                "aliases": ["Business Standard", "business-standard.com"],
            },
            "The Economic Times": {
                "tier": 2,
                "aliases": ["The Economic Times", "Economic Times", "economictimes.com"],
            },
            "TechCrunch": {
                "tier": 2,
                "aliases": ["TechCrunch", "techcrunch.com"],
            },
            "WIRED": {
                "tier": 2,
                "aliases": ["WIRED", "Wired", "wired.com"],
            },
            "Ars Technica": {
                "tier": 2,
                "aliases": ["Ars Technica", "arstechnica.com"],
            },
            "MIT Technology Review": {
                "tier": 2,
                "aliases": ["MIT Technology Review", "technologyreview.com"],
            },
            "The Verge": {
                "tier": 2,
                "aliases": ["The Verge", "theverge.com"],
            },
        },
    },
    "alerts": {
        "enabled": True,
        "minimum_score": 10.5,
        "minimum_sources": 2,
        "cooldown_hours": 6
    },
    "profile": {
        "name": "",
        "location": "India",
        "occupation": "",
        "interests": [
            "artificial intelligence",
            "technology",
            "India",
            "global affairs",
        ],
        "priority_topics": [
            "generative AI",
            "LLMs",
            "AI agents",
            "startups",
            "business",
            "geopolitics",
        ],
        "avoid_topics": ["celebrity gossip", "sports match recaps"],
        "briefing_style": "direct, analytical, useful, no hype",
    },
    "feeds": {
        "global": [
            "https://news.google.com/rss/search?q=(source%3AReuters%20OR%20source%3A%22Associated%20Press%22%20OR%20source%3ABBC%20OR%20source%3ABloomberg%20OR%20source%3A%22Financial%20Times%22)%20when%3A2d&hl=en-US&gl=US&ceid=US:en",
            "https://feeds.bbci.co.uk/news/world/rss.xml",
        ],
        "india": [
            "https://news.google.com/rss/search?q=(source%3A%22The%20Hindu%22%20OR%20source%3A%22The%20Indian%20Express%22%20OR%20source%3ANDTV%20OR%20source%3AReuters%20OR%20source%3A%22Hindustan%20Times%22)%20India%20when%3A2d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://feeds.feedburner.com/ndtvnews-top-stories",
        ],
        "ai_tech": [
            "https://news.google.com/rss/search?q=(artificial%20intelligence%20OR%20AI%20agents%20OR%20LLM)%20(source%3AReuters%20OR%20source%3ABloomberg%20OR%20source%3A%22Financial%20Times%22%20OR%20source%3AWIRED%20OR%20source%3A%22MIT%20Technology%20Review%22)%20when%3A2d&hl=en-US&gl=US&ceid=US:en",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
        ],
    },
    "newsapi_queries": {
        "global": "(geopolitics OR economy OR climate OR conflict) NOT sports",
        "india": "India AND (government OR economy OR policy OR technology)",
        "ai_tech": "(artificial intelligence OR LLM OR AI agent OR semiconductor)",
    },
    "source_weights": {
        "Reuters": 1.35,
        "Associated Press": 1.3,
        "BBC": 1.25,
        "Financial Times": 1.25,
        "Bloomberg": 1.2,
        "The Hindu": 1.25,
        "The Indian Express": 1.2,
        "Press Trust of India": 1.2,
        "TechCrunch": 1.08,
    },
}


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings(path: Path = DEFAULT_CONFIG) -> dict:
    _load_dotenv(ROOT / ".env")
    user_config = {}
    if path.exists():
        user_config = json.loads(path.read_text(encoding="utf-8"))

    settings = _deep_merge(DEFAULTS, user_config)
    settings.update(
        {
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "news_api_key": os.getenv("NEWS_API_KEY", ""),
            "gmail_address": os.getenv("GMAIL_ADDRESS", ""),
            "gmail_app_password": os.getenv("GMAIL_APP_PASSWORD", ""),
        }
    )
    settings["recipient"] = (
        os.getenv("DIGEST_RECIPIENT")
        or settings.get("recipient")
        or settings["gmail_address"]
    )
    return settings


def validate_settings(settings: dict, require_email: bool = True) -> list[str]:
    missing = []
    if require_email:
        if not settings["gmail_address"]:
            missing.append("GMAIL_ADDRESS")
        if not settings["gmail_app_password"]:
            missing.append("GMAIL_APP_PASSWORD")
        if not settings["recipient"]:
            missing.append("DIGEST_RECIPIENT or recipient in config.json")
    return missing
