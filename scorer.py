"""Arabic + Indonesian normalization and similarity scoring."""
import re

from rapidfuzz import fuzz

ARABIC_DIACRITICS = re.compile(r"[ً-ٰٟۖ-ۭ]")


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
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _similarity(ref: str, hyp: str) -> int:
    if not ref:
        return 0
    if not hyp:
        return 0
    token_set = fuzz.token_set_ratio(ref, hyp)
    partial = fuzz.partial_ratio(ref, hyp)
    return round(0.6 * token_set + 0.4 * partial)


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
    s_arab = _similarity(normalize_arabic(ref_arab), normalize_arabic(hyp_arab))
    s_artinya = _similarity(
        normalize_indonesian(ref_artinya),
        normalize_indonesian(hyp_artinya),
    )
    final = round(0.6 * s_arab + 0.4 * s_artinya)
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
