from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


WORD_RE = re.compile(r"[a-z0-9]+")
TRACKING_PARAMS = {"fbclid", "gclid", "ocid", "ref", "ref_src"}


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), "")
    )


def title_tokens(title: str) -> set[str]:
    return {word for word in WORD_RE.findall(title.lower()) if len(word) > 2}


@dataclass
class Article:
    title: str
    description: str
    url: str
    source: str
    published_at: datetime
    category: str
    image_url: str = ""
    score: float = 0.0
    score_reasons: tuple[str, ...] = ()
    corroborating_sources: tuple[str, ...] = ()
    corroborating_urls: tuple[str, ...] = ()
    confidence: str = "single-source"

    @property
    def fingerprint(self) -> str:
        basis = canonical_url(self.url) or " ".join(sorted(title_tokens(self.title)))
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]

    @property
    def age_hours(self) -> float:
        now = datetime.now(timezone.utc)
        published = self.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return max(0.0, (now - published).total_seconds() / 3600)

    def prompt_dict(self) -> dict:
        return {
            "id": self.fingerprint,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "url": self.url,
            "image_url": self.image_url,
            "ranking_score": round(self.score, 2),
            "ranking_reasons": list(self.score_reasons),
            "corroborating_sources": list(self.corroborating_sources),
            "confidence": self.confidence,
        }

    def to_state_dict(self) -> dict:
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        return data
