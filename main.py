from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import ROOT, load_settings, validate_settings
from fetcher import fetch_news
from memory import load_memory, memory_summary, record_feedback
from ranking import rank_and_dedupe, select_candidates
from sender import render_text, save_preview, send_alert, send_digest
from summarizer import hydrate_digest, summarize


STATE_PATH = ROOT / "data" / "state.json"
PREVIEW_PATH = ROOT / "output" / "latest_digest.html"
LOG_PATH = ROOT / "data" / "agent.log"


def _log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"{timestamp} {message}"
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"seen": {}, "last_success": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"seen": {}, "last_success": None}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    state["seen"] = {
        key: value
        for key, value in state.get("seen", {}).items()
        if datetime.fromisoformat(value) >= cutoff
    }
    state["alerts"] = {
        key: value
        for key, value in state.get("alerts", {}).items()
        if datetime.fromisoformat(value) >= cutoff
    }
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(STATE_PATH)


def run_agent(*, dry_run: bool = False, ignore_history: bool = False) -> int:
    settings = load_settings()
    missing = validate_settings(settings, require_email=not dry_run)
    if missing:
        _log("Configuration missing: " + ", ".join(missing))
        return 2

    state = _load_state()
    memory = load_memory()
    settings["learned_preferences"] = memory
    seen_ids = set() if ignore_history else set(state.get("seen", {}))

    _log("Collecting live news")
    articles = fetch_news(settings)
    _log(f"Collected {len(articles)} articles")
    if not articles:
        _log("No articles were collected; delivery cancelled")
        return 1

    ranked = rank_and_dedupe(articles, settings, seen_ids, memory)
    candidates = select_candidates(ranked, settings)
    counts = ", ".join(f"{key}={len(value)}" for key, value in candidates.items())
    _log(f"Ranked unseen candidates: {counts}")

    digest = summarize(candidates, settings)
    digest, used_articles = hydrate_digest(digest, candidates)
    save_preview(digest, settings, PREVIEW_PATH)
    _log(f"Preview written to {PREVIEW_PATH}")

    if dry_run:
        print("\n" + render_text(digest))
        _log("Dry run complete; no email sent")
        return 0

    if not used_articles:
        _log("No editorially useful unseen stories; email skipped")
        return 0

    send_digest(digest, settings)
    sent_at = datetime.now(timezone.utc).isoformat()
    for article in used_articles:
        state.setdefault("seen", {})[article.fingerprint] = sent_at
    state["last_success"] = sent_at
    _save_state(state)
    _log(f"Email sent with {len(used_articles)} stories")
    return 0


def run_alert_scan(*, dry_run: bool = False) -> int:
    settings = load_settings()
    if not settings["alerts"].get("enabled", True):
        _log("Alerting is disabled")
        return 0
    missing = validate_settings(settings, require_email=not dry_run)
    if missing:
        _log("Configuration missing: " + ", ".join(missing))
        return 2

    state = _load_state()
    memory = load_memory()
    settings["learned_preferences"] = memory
    articles = fetch_news(settings)
    cooldown = timedelta(hours=float(settings["alerts"]["cooldown_hours"]))
    now = datetime.now(timezone.utc)
    alert_seen = {
        key
        for key, value in state.get("alerts", {}).items()
        if datetime.fromisoformat(value) >= now - cooldown
    }
    ranked = rank_and_dedupe(articles, settings, alert_seen, memory)
    minimum_score = float(settings["alerts"]["minimum_score"])
    minimum_sources = int(settings["alerts"]["minimum_sources"])
    eligible = [
        article
        for article in ranked
        if article.score >= minimum_score
        and len(article.corroborating_sources) >= minimum_sources
    ]
    if not eligible:
        _log("Alert scan complete; no corroborated high-priority event")
        return 0

    article = eligible[0]
    if dry_run:
        print(
            f"ALERT CANDIDATE\n{article.title}\nScore: {article.score}\n"
            f"Sources: {', '.join(article.corroborating_sources)}\n{article.url}"
        )
        return 0

    send_alert(article, settings)
    state.setdefault("alerts", {})[article.fingerprint] = datetime.now(timezone.utc).isoformat()
    _save_state(state)
    _log(f"Sent intelligence alert: {article.title}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Personal 7 AM news intelligence agent")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["brief", "alert-scan", "feedback", "status"],
        default="brief",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build a preview without email")
    parser.add_argument(
        "--ignore-history",
        action="store_true",
        help="Include stories that may have appeared in an earlier digest",
    )
    parser.add_argument(
        "--like-topic",
        help="Teach the agent to favor a topic or phrase",
    )
    parser.add_argument(
        "--dislike-topic",
        help="Teach the agent to downrank a topic or phrase",
    )
    parser.add_argument("--trust-source", help="Teach the agent to favor a source")
    parser.add_argument("--mute-source", help="Teach the agent to downrank a source")
    return parser.parse_args()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    try:
        if args.command == "feedback":
            feedback = [
                ("like_topic", args.like_topic),
                ("dislike_topic", args.dislike_topic),
                ("trust_source", args.trust_source),
                ("mute_source", args.mute_source),
            ]
            supplied = [(kind, value) for kind, value in feedback if value]
            if not supplied:
                print("Provide one feedback option, such as --like-topic \"AI agents\".")
                sys.exit(2)
            for kind, value in supplied:
                record_feedback(kind, value)
            print(memory_summary(load_memory()))
            sys.exit(0)
        if args.command == "status":
            state = _load_state()
            print(memory_summary(load_memory()))
            print(f"Last successful briefing: {state.get('last_success') or 'never'}")
            print(f"Remembered stories: {len(state.get('seen', {}))}")
            print(f"Remembered alerts: {len(state.get('alerts', {}))}")
            sys.exit(0)
        if args.command == "alert-scan":
            sys.exit(run_alert_scan(dry_run=args.dry_run))
        sys.exit(run_agent(dry_run=args.dry_run, ignore_history=args.ignore_history))
    except Exception as exc:
        _log(f"Fatal error: {type(exc).__name__}: {exc}")
        raise
