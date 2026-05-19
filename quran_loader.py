"""Load Juz 30 + Al-Fatihah content from JSON."""
import json
import os
import random

CONTENT_PATH = os.path.join(
    os.path.dirname(__file__), "content", "juz30.json"
)

_CACHE = {}


def _load():
    if "all" in _CACHE:
        return _CACHE["all"]
    if not os.path.exists(CONTENT_PATH):
        _CACHE["all"] = []
        return []
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        _CACHE["all"] = json.load(f)
    return _CACHE["all"]


def all_surat_sorted():
    """All 38 surat ordered by surat number (1, 78, 79, …, 114)."""
    return sorted(_load(), key=lambda s: s["nomor"])


def find(surat_id: str):
    for s in _load():
        if s.get("id") == surat_id:
            return s
    return None


def random_surat():
    pool = _load()
    return random.choice(pool) if pool else None


def neighbors(surat_id: str):
    """Prev/next surat by nomor order, wrapping at boundaries."""
    pool = all_surat_sorted()
    if not pool:
        return None, None, 0, 0
    ids = [s["id"] for s in pool]
    try:
        idx = ids.index(surat_id)
    except ValueError:
        return None, None, 0, len(pool)
    if len(pool) <= 1:
        return None, None, 1, 1
    prev_s = pool[(idx - 1) % len(pool)]
    next_s = pool[(idx + 1) % len(pool)]
    return prev_s, next_s, idx + 1, len(pool)
