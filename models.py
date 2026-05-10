"""SQLite schema and data-access helpers for the exam app."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "exam.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    score REAL NOT NULL,
    correct_count INTEGER,
    wrong_count INTEGER,
    blank_count INTEGER,
    time_used_seconds INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attempt_answers (
    attempt_id INTEGER REFERENCES attempts(id),
    question_id INTEGER,
    student_answer TEXT,
    correct_answer TEXT,
    is_correct INTEGER
);

CREATE TABLE IF NOT EXISTS seen_questions (
    student_name TEXT,
    subject TEXT,
    question_id INTEGER,
    last_seen_at DATETIME,
    times_seen INTEGER DEFAULT 1,
    PRIMARY KEY (student_name, subject, question_id)
);

CREATE INDEX IF NOT EXISTS idx_attempts_subject ON attempts(subject);
CREATE INDEX IF NOT EXISTS idx_attempts_student ON attempts(LOWER(student_name));
CREATE INDEX IF NOT EXISTS idx_seen_student_subject ON seen_questions(LOWER(student_name), subject);
"""


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def normalize_name(name: str) -> str:
    return (name or "").strip()


def name_key(name: str) -> str:
    return normalize_name(name).lower()


def save_attempt(student_name, subject, score, correct, wrong, blank, time_used, answers):
    """Persist an attempt + per-question answers + update seen_questions.

    `answers` is a list of dicts: {question_id, student_answer, correct_answer, is_correct}
    """
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO attempts
               (student_name, subject, score, correct_count, wrong_count, blank_count, time_used_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (student_name.strip(), subject, score, correct, wrong, blank, time_used),
        )
        attempt_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO attempt_answers
               (attempt_id, question_id, student_answer, correct_answer, is_correct)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    attempt_id,
                    a["question_id"],
                    a.get("student_answer"),
                    a["correct_answer"],
                    1 if a["is_correct"] else 0,
                )
                for a in answers
            ],
        )
        now = datetime.utcnow().isoformat(timespec="seconds")
        for a in answers:
            conn.execute(
                """INSERT INTO seen_questions (student_name, subject, question_id, last_seen_at, times_seen)
                   VALUES (?, ?, ?, ?, 1)
                   ON CONFLICT(student_name, subject, question_id)
                   DO UPDATE SET last_seen_at = excluded.last_seen_at,
                                 times_seen = seen_questions.times_seen + 1""",
                (student_name.strip(), subject, a["question_id"], now),
            )
        return attempt_id


def get_seen_question_ids(student_name, subject):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT question_id, last_seen_at, times_seen FROM seen_questions
               WHERE LOWER(student_name) = ? AND subject = ?""",
            (name_key(student_name), subject),
        ).fetchall()
    return [(r["question_id"], r["last_seen_at"], r["times_seen"]) for r in rows]


def reset_seen_questions(student_name, subject):
    with get_conn() as conn:
        conn.execute(
            """DELETE FROM seen_questions
               WHERE LOWER(student_name) = ? AND subject = ?""",
            (name_key(student_name), subject),
        )


def leaderboard(subject):
    """Best score per student for a subject, ordered desc."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT student_name,
                      MAX(score) AS best_score,
                      COUNT(*) AS attempts_count,
                      MAX(timestamp) AS last_attempt
               FROM attempts
               WHERE subject = ?
               GROUP BY LOWER(student_name)
               ORDER BY best_score DESC, last_attempt ASC""",
            (subject,),
        ).fetchall()
    return [dict(r) for r in rows]


def subject_stats(subject):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(DISTINCT LOWER(student_name)) AS participants,
                      AVG(score) AS avg_score,
                      COUNT(*) AS total_attempts
               FROM attempts WHERE subject = ?""",
            (subject,),
        ).fetchone()
    return dict(row) if row else {}


def student_attempts(student_name):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, subject, score, correct_count, wrong_count, blank_count,
                      time_used_seconds, timestamp
               FROM attempts
               WHERE LOWER(student_name) = ?
               ORDER BY timestamp DESC""",
            (name_key(student_name),),
        ).fetchall()
    return [dict(r) for r in rows]


def attempt_detail(attempt_id):
    with get_conn() as conn:
        attempt = conn.execute(
            "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
        answers = conn.execute(
            """SELECT question_id, student_answer, correct_answer, is_correct
               FROM attempt_answers WHERE attempt_id = ?""",
            (attempt_id,),
        ).fetchall()
    return dict(attempt) if attempt else None, [dict(a) for a in answers]


def student_subject_summary(student_name):
    """Per-subject stats for a single student."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT subject,
                      COUNT(*) AS attempts_count,
                      MAX(score) AS best_score,
                      MIN(score) AS worst_score,
                      AVG(score) AS avg_score
               FROM attempts
               WHERE LOWER(student_name) = ?
               GROUP BY subject""",
            (name_key(student_name),),
        ).fetchall()
    return [dict(r) for r in rows]
