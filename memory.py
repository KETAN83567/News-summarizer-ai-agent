from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import ROOT


MEMORY_PATH = ROOT / "data" / "preferences.json"


def load_memory(path: Path = MEMORY_PATH) -> dict:
    if not path.exists():
        return {"topics": {}, "sources": {}, "feedback": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"topics": {}, "sources": {}, "feedback": []}
    data.setdefault("topics", {})
    data.setdefault("sources", {})
    data.setdefault("feedback", [])
    return data


def save_memory(memory: dict, path: Path = MEMORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(memory, indent=2), encoding="utf-8")
    temp.replace(path)


def record_feedback(kind: str, value: str, path: Path = MEMORY_PATH) -> dict:
    if kind not in {"like_topic", "dislike_topic", "trust_source", "mute_source"}:
        raise ValueError(f"Unknown feedback type: {kind}")
    clean_value = value.strip()
    if not clean_value:
        raise ValueError("Feedback value cannot be empty")

    memory = load_memory(path)
    bucket = "topics" if kind.endswith("topic") else "sources"
    delta = 1.0 if kind in {"like_topic", "trust_source"} else -1.0
    current = float(memory[bucket].get(clean_value, 0))
    memory[bucket][clean_value] = max(-5.0, min(5.0, current + delta))
    memory["feedback"].append(
        {
            "type": kind,
            "value": clean_value,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    memory["feedback"] = memory["feedback"][-200:]
    save_memory(memory, path)
    return memory


def memory_summary(memory: dict) -> str:
    liked = sorted(
        ((name, score) for name, score in memory.get("topics", {}).items() if score > 0),
        key=lambda item: item[1],
        reverse=True,
    )
    disliked = sorted(
        ((name, score) for name, score in memory.get("topics", {}).items() if score < 0),
        key=lambda item: item[1],
    )
    trusted = sorted(
        ((name, score) for name, score in memory.get("sources", {}).items() if score > 0),
        key=lambda item: item[1],
        reverse=True,
    )
    muted = sorted(
        ((name, score) for name, score in memory.get("sources", {}).items() if score < 0),
        key=lambda item: item[1],
    )
    return "\n".join(
        [
            "Learned preferences:",
            f"  Liked topics: {liked or 'none yet'}",
            f"  Disliked topics: {disliked or 'none yet'}",
            f"  Trusted sources: {trusted or 'none yet'}",
            f"  Muted sources: {muted or 'none yet'}",
            f"  Feedback events: {len(memory.get('feedback', []))}",
        ]
    )
