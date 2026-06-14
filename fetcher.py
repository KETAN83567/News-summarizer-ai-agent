from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

from models import Article


USER_AGENT = "PersonalMorningBriefing/2.0 (+local news assistant)"
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
INVISIBLE_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
SOURCE_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
BLOCKED_EMBED_HOSTS = {"c.ndtvimg.com"}


def _clean(value: str | None) -> str:
    text = html.unescape(value or "")
    text = TAG_RE.sub(" ", text)
    text = INVISIBLE_RE.sub("", text)
    return SPACE_RE.sub(" ", text).strip()


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _download(url: str, timeout: int = 18) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _normalize_source(value: str) -> str:
    normalized = SOURCE_NORMALIZE_RE.sub(" ", value.lower()).strip()
    return normalized.removeprefix("www ")


def trusted_source_name(source: str, settings: dict) -> str | None:
    policy = settings.get("source_policy", {})
    sources = policy.get("sources", {})
    minimum_tier = int(policy.get("minimum_tier", 2))
    normalized = _normalize_source(source)
    if not normalized:
        return None

    for canonical, metadata in sources.items():
        if int(metadata.get("tier", 99)) > minimum_tier:
            continue
        aliases = metadata.get("aliases", []) + [canonical]
        for alias in aliases:
            candidate = _normalize_source(alias)
            if normalized == candidate:
                return canonical
            if "." in alias and (
                normalized.endswith(candidate) or candidate.endswith(normalized)
            ):
                return canonical
    return None


def filter_trusted_sources(articles: list[Article], settings: dict) -> list[Article]:
    policy = settings.get("source_policy", {})
    if not policy.get("strict", False):
        return articles

    trusted = []
    for article in articles:
        canonical = trusted_source_name(article.source, settings)
        if canonical:
            article.source = canonical
            trusted.append(article)
    print(
        f"Trusted-source policy kept {len(trusted)} of {len(articles)} collected articles"
    )
    return trusted


def _image_is_available(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Range": "bytes=0-1023",
            },
        )
        with urllib.request.urlopen(request, timeout=6) as response:
            return response.headers.get_content_type().startswith("image/")
    except Exception:
        return False


def _normalize_image_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() in BLOCKED_EMBED_HOSTS:
        return ""
    if "ichef.bbci.co.uk" in parsed.netloc:
        return url.replace("/standard/240/", "/standard/1024/")
    return url


def validate_article_images(articles: list[Article]) -> list[Article]:
    cache: dict[str, bool] = {}
    for article in articles:
        if not article.image_url:
            continue
        article.image_url = _normalize_image_url(article.image_url)
        if not article.image_url:
            continue
        if article.image_url not in cache:
            cache[article.image_url] = _image_is_available(article.image_url)
        available = cache[article.image_url]
        if not available:
            article.image_url = ""
    return articles


def fetch_rss(url: str, category: str, limit: int = 25) -> list[Article]:
    """Fetch RSS or Atom while keeping the metadata needed for ranking."""
    try:
        root = ET.fromstring(_download(url))
    except Exception as exc:
        print(f"Warning: feed failed ({url}): {exc}")
        return []

    articles: list[Article] = []
    entries = root.findall(".//item")
    is_atom = not entries
    if is_atom:
        entries = root.findall(".//{*}entry")

    for entry in entries[:limit]:
        if is_atom:
            title = entry.findtext("{*}title", "")
            description = (
                entry.findtext("{*}summary", "")
                or entry.findtext("{*}content", "")
            )
            link_node = entry.find("{*}link")
            link = link_node.get("href", "") if link_node is not None else ""
            published = (
                entry.findtext("{*}published", "")
                or entry.findtext("{*}updated", "")
            )
            source = urllib.parse.urlparse(link).netloc
            image_url = ""
            for node in entry.findall("{*}link"):
                if node.get("rel") == "enclosure" and node.get("type", "").startswith("image/"):
                    image_url = node.get("href", "")
                    break
            if not image_url:
                media = entry.find("{*}thumbnail")
                if media is None:
                    media = entry.find("{*}content")
                if media is not None and media.get("url"):
                    image_url = media.get("url", "")
        else:
            title = entry.findtext("title", "")
            description = (
                entry.findtext("description", "")
                or entry.findtext("{*}encoded", "")
            )
            link = entry.findtext("link", "")
            published = entry.findtext("pubDate", "")
            source = entry.findtext("source", "")
            image_url = ""
            media = entry.find("{*}thumbnail")
            if media is None:
                media = entry.find("{*}content")
            if media is not None and media.get("url"):
                image_url = media.get("url", "")
            if not image_url:
                enclosure = entry.find("enclosure")
                if (
                    enclosure is not None
                    and enclosure.get("type", "").startswith("image/")
                ):
                    image_url = enclosure.get("url", "")

        title = _clean(title)
        link = _clean(link)
        if not title or not link or "[Removed]" in title:
            continue

        if not source:
            source = urllib.parse.urlparse(link).netloc.removeprefix("www.")

        articles.append(
            Article(
                title=title,
                description=_clean(description)[:1000],
                url=link,
                source=_clean(source) or "Unknown source",
                published_at=_parse_date(published),
                category=category,
                image_url=_clean(image_url),
            )
        )
    return articles


def fetch_newsapi(category: str, query: str, api_key: str, limit: int = 30) -> list[Article]:
    endpoint = "https://newsapi.org/v2/everything"
    params = urllib.parse.urlencode(
        {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(limit, 100),
            "apiKey": api_key,
        }
    )
    try:
        payload = json.loads(_download(f"{endpoint}?{params}"))
    except Exception as exc:
        print(f"Warning: NewsAPI failed for {category}: {exc}")
        return []

    if payload.get("status") != "ok":
        print(f"Warning: NewsAPI error: {payload.get('message', 'unknown error')}")
        return []

    results: list[Article] = []
    for item in payload.get("articles", []):
        title = _clean(item.get("title"))
        url = item.get("url") or ""
        if not title or not url or "[Removed]" in title:
            continue
        results.append(
            Article(
                title=title,
                description=_clean(item.get("description"))[:1000],
                url=url,
                source=_clean((item.get("source") or {}).get("name")) or "NewsAPI",
                published_at=_parse_date(item.get("publishedAt")),
                category=category,
                image_url=_clean(item.get("urlToImage")),
            )
        )
    return results


def fetch_news(settings: dict) -> list[Article]:
    """Collect all configured feeds plus optional NewsAPI coverage."""
    articles: list[Article] = []
    for category, urls in settings["feeds"].items():
        for url in urls:
            articles.extend(fetch_rss(url, category))

    api_key = settings.get("news_api_key")
    if api_key:
        for category, query in settings["newsapi_queries"].items():
            articles.extend(fetch_newsapi(category, query, api_key))

    return validate_article_images(filter_trusted_sources(articles, settings))


def group_by_category(articles: Iterable[Article]) -> dict[str, list[Article]]:
    grouped = {"global": [], "india": [], "ai_tech": []}
    for article in articles:
        grouped.setdefault(article.category, []).append(article)
    return grouped
