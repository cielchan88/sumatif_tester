"""Load doa/hadits content from JSON and filter by grade."""
import json
import os
import random

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "content")

CATEGORIES = {
    "doa": {
        "label": "Doa",
        "label_plural": "Doa",
        "icon": "🤲",
        "file": "doa.json",
    },
    "hadits": {
        "label": "Hadits",
        "label_plural": "Hadits",
        "icon": "📖",
        "file": "hadits.json",
    },
}

_CACHE = {}


def _load(category: str):
    if category not in CATEGORIES:
        return []
    if category in _CACHE:
        return _CACHE[category]
    path = os.path.join(CONTENT_DIR, CATEGORIES[category]["file"])
    if not os.path.exists(path):
        _CACHE[category] = []
        return []
    with open(path, "r", encoding="utf-8") as f:
        _CACHE[category] = json.load(f)
    return _CACHE[category]


def all_items(category: str):
    return list(_load(category))


def items_by_grade(category: str, grade: int):
    """grade=0 means all grades."""
    items = _load(category)
    if grade == 0:
        return list(items)
    return [it for it in items if it.get("grade") == grade]


def find_item(category: str, item_id: str):
    for it in _load(category):
        if it.get("id") == item_id:
            return it
    return None


def random_item(category: str, grade: int):
    items = items_by_grade(category, grade)
    if not items:
        return None
    return random.choice(items)


def grade_counts(category: str):
    """Return dict {1: count, 2: count, ..., 0: total}."""
    items = _load(category)
    counts = {g: 0 for g in range(1, 6)}
    for it in items:
        g = it.get("grade")
        if g in counts:
            counts[g] += 1
    counts[0] = sum(counts.values())
    return counts


def neighbors(category: str, grade: int, item_id: str):
    """Return (prev_item, next_item, position, total) within the given grade.

    Wraps around at boundaries so navigation is always available. Ordered by
    `nomor` so it follows the silabus sequence.
    """
    items = sorted(
        items_by_grade(category, grade),
        key=lambda it: it.get("nomor", 0),
    )
    if not items:
        return None, None, 0, 0
    ids = [it["id"] for it in items]
    try:
        idx = ids.index(item_id)
    except ValueError:
        return None, None, 0, len(items)
    prev_item = items[(idx - 1) % len(items)] if len(items) > 1 else None
    next_item = items[(idx + 1) % len(items)] if len(items) > 1 else None
    return prev_item, next_item, idx + 1, len(items)
