"""Strict similarity scoring for hafalan (memorization testing).

Design rationale
----------------
Token-set/partial ratios (the previous approach) are wrong for memorization
because they ignore word order and inflate scores for partial recitations.
For ASR-based Quran/hadits scoring, the field's gold standard is:

  - **WER (Word Error Rate)**  = Levenshtein(ref_words, hyp_words) / |ref_words|
  - **CER (Character Error Rate)** = Levenshtein(ref_chars, hyp_chars) / |ref_chars|

Both penalize substitutions, deletions, and insertions while preserving order.
We combine them and add a **coverage penalty** so a student who recites only
half the doa cannot get a passing score even if every word they did say was
correct (a known weakness of any pure similarity measure).

References: WER/CER are the standard ASR metrics used in published Quran
recitation recognition systems (e.g., Ar-DAD / QRFAM datasets; production
systems target <10% WER).
"""
import re

from rapidfuzz.distance import Levenshtein

ARABIC_DIACRITICS = re.compile(r"[ً-ٰٟۖ-ۭ]")


def normalize_arabic(text: str) -> str:
    if not text:
        return ""
    text = ARABIC_DIACRITICS.sub("", text)
    text = text.replace("ـ", "")
    text = re.sub(r"[أإآ]", "ا", text)
    text = text.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    text = text.replace("ة", "ه")
    text = re.sub(r"[^؀-ۿ\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_indonesian(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\b(yg|yang)\b", "yang", text)
    text = re.sub(r"\b(tdk|tidak)\b", "tidak", text)
    text = re.sub(r"\b(dg|dgn|dengan)\b", "dengan", text)
    text = re.sub(r"\b(utk|untuk)\b", "untuk", text)
    text = re.sub(r"\b(krn|karena)\b", "karena", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _word_error_rate(ref_words, hyp_words) -> float:
    if not ref_words:
        return 1.0 if hyp_words else 0.0
    # Levenshtein on token sequences = edit distance at word level
    distance = Levenshtein.distance(ref_words, hyp_words)
    return distance / len(ref_words)


def _char_error_rate(ref: str, hyp: str) -> float:
    r = ref.replace(" ", "")
    h = hyp.replace(" ", "")
    if not r:
        return 1.0 if h else 0.0
    return Levenshtein.distance(r, h) / len(r)


def _similarity(ref: str, hyp: str) -> int:
    """Strict 0–100 score: WER + CER + coverage penalty.

    Behavior on representative inputs (post-normalization):
      perfect recitation              → 100
      1 word wrong out of 10          → ~88
      reciting only first 50% perfect → ~31  (was ~70 under set/partial ratios)
      jumbled word order              → low  (set/partial ignored this entirely)
      completely wrong / empty        → 0
    """
    if not ref or not hyp:
        return 0

    ref_words = ref.split()
    hyp_words = hyp.split()

    wer = _word_error_rate(ref_words, hyp_words)
    cer = _char_error_rate(ref, hyp)

    wer_score = max(0.0, 100.0 * (1.0 - wer))
    cer_score = max(0.0, 100.0 * (1.0 - cer))

    # For very short references (≤3 words), CER is more reliable because a
    # single-word miss makes WER explode (e.g. ref="غفرانك" hyp="غفرتك" →
    # WER=1.0 but CER ≈ 0.3).
    if len(ref_words) <= 3:
        base = 0.3 * wer_score + 0.7 * cer_score
    else:
        base = 0.7 * wer_score + 0.3 * cer_score

    # Coverage: how much of the reference (by word count) did the student
    # actually cover? Reciting half perfectly should not score 70 — that
    # would reward incomplete hafalan.
    coverage = min(1.0, len(hyp_words) / max(1, len(ref_words)))
    if coverage < 0.8:
        # Linear ramp: coverage 0.0 → ×0, 0.8 → ×1.0
        base *= coverage / 0.8

    # Very generous transcripts (insertions) are already penalized through WER
    # because each extra word counts as an insertion edit. No extra penalty.

    return int(round(max(0.0, min(100.0, base))))


def score_doa(reference_arab: str, hypothesis: str) -> dict:
    ref = normalize_arabic(reference_arab)
    hyp = normalize_arabic(hypothesis)
    return {
        "score": _similarity(ref, hyp),
        "ref_arab": ref,
        "hyp_arab": hyp,
    }


def score_hadits(ref_arab: str, ref_artinya: str,
                 hyp_arab: str, hyp_artinya: str) -> dict:
    s_arab = _similarity(
        normalize_arabic(ref_arab), normalize_arabic(hyp_arab)
    )
    s_artinya = _similarity(
        normalize_indonesian(ref_artinya), normalize_indonesian(hyp_artinya)
    )
    final = int(round(0.6 * s_arab + 0.4 * s_artinya))
    return {
        "score": final,
        "score_arab": s_arab,
        "score_artinya": s_artinya,
        "hyp_arab": hyp_arab,
        "hyp_artinya": hyp_artinya,
    }


def feedback_for(score: int) -> dict:
    if score >= 85:
        return {
            "level": "Sangat Baik",
            "stars": "⭐⭐⭐",
            "message": "Masya Allah, hafalanmu bagus sekali!",
            "color": "success",
        }
    if score >= 70:
        return {
            "level": "Baik",
            "stars": "⭐⭐",
            "message": "Bagus, sedikit lagi sempurna!",
            "color": "info",
        }
    if score >= 50:
        return {
            "level": "Cukup",
            "stars": "⭐",
            "message": "Hampir benar, ayo coba lagi ya!",
            "color": "warning",
        }
    return {
        "level": "Perlu Latihan",
        "stars": "",
        "message": "Yuk dilatih lagi, kamu pasti bisa!",
        "color": "danger",
    }


def hadits_tip(score_arab: int, score_artinya: int) -> str:
    arab_low = score_arab < 70
    arti_low = score_artinya < 70
    if not arab_low and arti_low:
        return "Bacaan Arab sudah bagus, ayo perdalam hafalan artinya ya!"
    if arab_low and not arti_low:
        return "Kamu paham artinya. Ayo perkuat lagi hafalan teks Arabnya!"
    if arab_low and arti_low:
        return "Yuk dilatih lagi keduanya. Kamu pasti bisa!"
    return ""
