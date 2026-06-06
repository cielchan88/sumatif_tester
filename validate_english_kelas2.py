"""Validate questions/english_kelas2.json against the existing schema.

Run: python validate_english_kelas2.py
"""
import json
import os
import sys
from collections import Counter

PATH = os.path.join(os.path.dirname(__file__), "questions", "english_kelas2.json")
EXPECTED_LESSONS = {
    "Lesson 7: At the Farm",
    "Lesson 8: My Town",
    "Lesson 9: Our Clothes",
    "Lesson 10: Our Hobbies",
    "Lesson 12: On Holiday",
}
ALLOWED_DIFFICULTY = {"easy", "medium", "hard"}
ALLOWED_LETTERS = {"A", "B", "C", "D"}

def main():
    if not os.path.exists(PATH):
        print(f"ERROR: {PATH} not found")
        sys.exit(1)
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)

    errors = []
    questions = data.get("questions", [])

    # 1. Top-level shape
    if "subject" not in data or "questions" not in data:
        errors.append("Missing top-level 'subject' or 'questions' key")

    # 2. Minimum count
    if len(questions) < 60:
        errors.append(f"Need ≥60 questions, found {len(questions)}")

    seen_ids = set()
    seen_questions = set()
    lesson_counts = Counter()
    difficulty_counts = Counter()

    for q in questions:
        qid = q.get("id")
        if qid is None:
            errors.append(f"Question missing id: {q.get('question', '?')[:40]}")
            continue
        if not isinstance(qid, int):
            errors.append(f"id must be int: {qid}")
        if qid in seen_ids:
            errors.append(f"Duplicate id: {qid}")
        seen_ids.add(qid)

        # Required fields
        for field in ("topic", "difficulty", "question", "options", "correct_answer", "explanation"):
            if field not in q:
                errors.append(f"Q{qid} missing field: {field}")
                continue

        # Lesson check
        topic = q.get("topic", "")
        lesson_counts[topic] += 1
        if topic not in EXPECTED_LESSONS:
            errors.append(f"Q{qid} unknown lesson: {topic}")

        # Difficulty
        diff = q.get("difficulty")
        difficulty_counts[diff] += 1
        if diff not in ALLOWED_DIFFICULTY:
            errors.append(f"Q{qid} invalid difficulty: {diff}")

        # Options: exactly A B C D
        opts = q.get("options", {})
        if set(opts.keys()) != ALLOWED_LETTERS:
            errors.append(f"Q{qid} options must be exactly A/B/C/D, got {sorted(opts.keys())}")
        else:
            for letter, text in opts.items():
                if not isinstance(text, str) or not text.strip():
                    errors.append(f"Q{qid} option {letter} is empty")

        # correct_answer points to a real option letter
        ca = q.get("correct_answer")
        if ca not in ALLOWED_LETTERS:
            errors.append(f"Q{qid} correct_answer must be A/B/C/D, got {ca!r}")
        elif ca not in opts:
            errors.append(f"Q{qid} correct_answer {ca} not in options")

        # Question text non-empty
        if not isinstance(q.get("question"), str) or not q["question"].strip():
            errors.append(f"Q{qid} question text is empty")

        # Duplicate detection: combine question stem + sorted option texts so
        # two questions with the same stem ("Choose the correct sentence:") but
        # different choices don't false-positive.
        opt_signature = "|".join(sorted((t or "").strip().lower() for t in opts.values()))
        norm = " ".join(q.get("question", "").lower().split()) + "##" + opt_signature
        if norm in seen_questions:
            errors.append(f"Q{qid} duplicate of an earlier question")
        seen_questions.add(norm)

    # 3. Per-lesson coverage
    missing = EXPECTED_LESSONS - set(lesson_counts.keys())
    if missing:
        errors.append(f"No questions for lesson(s): {missing}")
    for lesson in EXPECTED_LESSONS:
        if lesson_counts.get(lesson, 0) < 12:
            errors.append(f"Lesson '{lesson}' has only {lesson_counts.get(lesson, 0)} questions (need ≥12)")

    # 4. Difficulty distribution reasonable (not all hard)
    if difficulty_counts.get("hard", 0) > len(questions) // 2:
        errors.append("More than half the questions are 'hard' — distribution skewed")

    # Report
    print(f"Total questions: {len(questions)}")
    print(f"Per lesson: {dict(lesson_counts)}")
    print(f"Per difficulty: {dict(difficulty_counts)}")
    print()

    if errors:
        print(f"VALIDATION FAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("✓ All checks passed.")


if __name__ == "__main__":
    main()
