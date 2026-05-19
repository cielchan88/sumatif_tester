"""Scoring for Quran surat hafalan (full-surat and per-ayat modes).

Uses the same WER + CER + coverage approach as scorer.py (the Doa/Hadits
scorer), but adds bismillah tolerance for surat where bismillah is not the
first ayah.
"""
import re

from scorer import (
    normalize_arabic,
    _similarity as _strict_similarity,
    feedback_for,
)

# Matches optional leading basmalah after normalization. Normalization strips
# diacritics, so the form is fixed: "بسم الله الرحمن الرحيم".
_BISMILLAH = re.compile(
    r"^\s*بسم\s+ال+ل?ه\s+الرحمن\s+الرحيم\s*"
)


def strip_optional_bismillah(normalized: str) -> str:
    return _BISMILLAH.sub("", normalized).strip()


def score_full_surat(reference_full: str, hypothesis: str,
                     is_al_fatihah: bool = False) -> dict:
    """Score a full-surat recitation.

    For Al-Fatihah, bismillah counts as ayat 1 and must be present. For other
    surat (Juz 30), allow students to optionally start with bismillah without
    penalty.
    """
    ref = normalize_arabic(reference_full)
    hyp = normalize_arabic(hypothesis)
    if not is_al_fatihah:
        hyp = strip_optional_bismillah(hyp)
        ref = strip_optional_bismillah(ref)
    score = _strict_similarity(ref, hyp)
    return {
        "score": score,
        "ref": ref,
        "hyp": hyp,
    }


def score_per_ayat(reference_ayat_list, hypothesis_list) -> dict:
    """Score each ayat separately, then take the simple mean.

    `reference_ayat_list` is the list of reference ayat texts (in order).
    `hypothesis_list` is the same length, one transcript per ayat.
    """
    if len(reference_ayat_list) != len(hypothesis_list):
        return {"error": "jumlah_ayat_tidak_cocok"}

    per_ayat = []
    for i, (ref, hyp) in enumerate(zip(reference_ayat_list, hypothesis_list), 1):
        s = _strict_similarity(normalize_arabic(ref), normalize_arabic(hyp))
        per_ayat.append({"nomor": i, "score": s, "hyp": hyp})

    avg = int(round(sum(p["score"] for p in per_ayat) / max(1, len(per_ayat))))
    return {
        "score": avg,
        "ayat": per_ayat,
        "weakest": [p["nomor"] for p in per_ayat if p["score"] < 50],
    }


__all__ = [
    "normalize_arabic",
    "strip_optional_bismillah",
    "score_full_surat",
    "score_per_ayat",
    "feedback_for",
]
