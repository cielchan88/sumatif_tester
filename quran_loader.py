"""Load Juz 30 + Al-Fatihah content from JSON."""
import json
import os
import random

CONTENT_PATH = os.path.join(
    os.path.dirname(__file__), "content", "juz30.json"
)

KATEGORI = {
    "sangat-pendek": {"label": "Sangat Pendek", "range": "3–7 ayat"},
    "pendek": {"label": "Pendek", "range": "8–15 ayat"},
    "sedang": {"label": "Sedang", "range": "16–25 ayat"},
    "panjang": {"label": "Panjang", "range": "26+ ayat"},
    "semua": {"label": "Semua Surat", "range": "—"},
}

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


def all_surat():
    return list(_load())


def by_kategori(kategori: str):
    items = _load()
    if kategori == "semua":
        return sorted(items, key=lambda s: s["jumlah_ayat"])
    return sorted(
        [s for s in items if s.get("kategori") == kategori],
        key=lambda s: s["jumlah_ayat"],
    )


def find(surat_id: str):
    for s in _load():
        if s.get("id") == surat_id:
            return s
    return None


def random_from(kategori: str):
    pool = by_kategori(kategori)
    return random.choice(pool) if pool else None


def kategori_counts():
    items = _load()
    counts = {k: 0 for k in KATEGORI if k != "semua"}
    for s in items:
        k = s.get("kategori")
        if k in counts:
            counts[k] += 1
    counts["semua"] = sum(counts.values())
    return counts


def neighbors(kategori: str, surat_id: str):
    pool = by_kategori(kategori)
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
