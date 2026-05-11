"""Load question banks from JSON and sample with anti-repeat logic."""
import json
import os
import random
from collections import defaultdict

import models

QUESTIONS_DIR = os.path.join(os.path.dirname(__file__), "questions")

SUBJECTS = [
    {"key": "pai", "name": "Pendidikan Agama Islam", "lang": "id"},
    {"key": "pancasila", "name": "Pendidikan Pancasila", "lang": "id"},
    {"key": "bahasa_indonesia", "name": "Bahasa Indonesia", "lang": "id"},
    {"key": "bahasa_inggris", "name": "Bahasa Inggris", "lang": "en"},
    {"key": "matematika", "name": "Matematika", "lang": "en"},
    {"key": "ipa", "name": "IPA", "lang": "en"},
    {"key": "ips", "name": "IPS", "lang": "id"},
    {"key": "pjok", "name": "PJOK", "lang": "id"},
    {"key": "sbdp", "name": "SBDP", "lang": "id"},
]

SUBJECT_BY_NAME = {s["name"]: s for s in SUBJECTS}
SUBJECT_BY_KEY = {s["key"]: s for s in SUBJECTS}


def load_pool(subject_key):
    path = os.path.join(QUESTIONS_DIR, f"{subject_key}.json")
    if not os.path.exists(path):
        return {"subject": subject_key, "questions": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pool_size(subject_name):
    s = SUBJECT_BY_NAME.get(subject_name)
    if not s:
        return 0
    return len(load_pool(s["key"]).get("questions", []))


def _stratify_by_difficulty(questions):
    buckets = defaultdict(list)
    for q in questions:
        buckets[q.get("difficulty", "medium")].append(q)
    return buckets


def _sample_with_difficulty_ratio(pool, n, target_ratio=(0.4, 0.4, 0.2)):
    """Sample n questions while keeping difficulty distribution close to target."""
    buckets = _stratify_by_difficulty(pool)
    easy = buckets.get("easy", [])
    medium = buckets.get("medium", [])
    hard = buckets.get("hard", [])
    desired = {
        "easy": int(round(n * target_ratio[0])),
        "medium": int(round(n * target_ratio[1])),
        "hard": n - int(round(n * target_ratio[0])) - int(round(n * target_ratio[1])),
    }
    chosen = []
    available = {"easy": easy[:], "medium": medium[:], "hard": hard[:]}
    for level in ("easy", "medium", "hard"):
        random.shuffle(available[level])
        take = min(desired[level], len(available[level]))
        chosen.extend(available[level][:take])
        available[level] = available[level][take:]
    # Top up if some bucket was undersized
    if len(chosen) < n:
        leftovers = available["easy"] + available["medium"] + available["hard"]
        random.shuffle(leftovers)
        chosen.extend(leftovers[: n - len(chosen)])
    random.shuffle(chosen)
    return chosen[:n]


def sample_questions(student_name, subject_name, n=40):
    """Anti-repeat sampling.

    Returns (questions, status) where status ∈ {"normal", "mixed", "cycle_reset", "short_pool"}.
    """
    s = SUBJECT_BY_NAME[subject_name]
    pool = load_pool(s["key"]).get("questions", [])
    if not pool:
        return [], "empty"
    if len(pool) <= n:
        # Pool smaller than requested — use all, randomized
        return _shuffle_options(random.sample(pool, len(pool))), "short_pool"

    seen_rows = models.get_seen_question_ids(student_name, subject_name)
    seen_map = {qid: (last, times) for qid, last, times in seen_rows}
    seen_ids = set(seen_map.keys())

    unseen = [q for q in pool if q["id"] not in seen_ids]
    status = "normal"

    if len(unseen) >= n:
        chosen = _sample_with_difficulty_ratio(unseen, n)
    elif len(unseen) > 0:
        # Take all unseen, then top up with least-recently-seen.
        chosen = list(unseen)
        seen_pool = [q for q in pool if q["id"] in seen_ids]
        seen_pool.sort(key=lambda q: seen_map.get(q["id"], ("", 0))[0] or "")
        chosen.extend(seen_pool[: n - len(chosen)])
        random.shuffle(chosen)
        status = "mixed"
    else:
        # All seen — reset and sample fresh.
        models.reset_seen_questions(student_name, subject_name)
        chosen = _sample_with_difficulty_ratio(pool, n)
        status = "cycle_reset"

    return _shuffle_options(chosen), status


def _shuffle_options(questions):
    """Return new question dicts with shuffled options A/B/C/D and adjusted correct_answer."""
    shuffled = []
    letters = ["A", "B", "C", "D"]
    for q in questions:
        opts = q["options"]
        items = [(k, opts[k]) for k in letters if k in opts]
        random.shuffle(items)
        new_opts = {letters[i]: items[i][1] for i in range(len(items))}
        new_correct = None
        for new_k, (orig_k, _) in zip(letters, items):
            if orig_k == q["correct_answer"]:
                new_correct = new_k
                break
        shuffled.append(
            {
                "id": q["id"],
                "topic": q.get("topic", ""),
                "difficulty": q.get("difficulty", "medium"),
                "question": q["question"],
                "options": new_opts,
                "correct_answer": new_correct,
                "explanation": q.get("explanation", ""),
            }
        )
    return shuffled


def find_question(subject_name, qid):
    s = SUBJECT_BY_NAME.get(subject_name)
    if not s:
        return None
    for q in load_pool(s["key"]).get("questions", []):
        if q["id"] == qid:
            return q
    return None
