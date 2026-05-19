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

CREATE TABLE IF NOT EXISTS hafalan_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    category TEXT NOT NULL,
    grade INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    item_title TEXT NOT NULL,
    score INTEGER NOT NULL,
    score_arab INTEGER,
    score_artinya INTEGER,
    transcript_arab TEXT,
    transcript_artinya TEXT,
    reference_arab TEXT,
    reference_artinya TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hafalan_student
    ON hafalan_attempts(LOWER(student_name));
CREATE INDEX IF NOT EXISTS idx_hafalan_category
    ON hafalan_attempts(category, grade);

CREATE TABLE IF NOT EXISTS quran_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    surat_id TEXT NOT NULL,
    surat_nomor INTEGER NOT NULL,
    surat_nama TEXT NOT NULL,
    kategori TEXT NOT NULL,
    mode TEXT NOT NULL,
    jumlah_ayat INTEGER NOT NULL,
    score INTEGER NOT NULL,
    score_per_ayat TEXT,
    transcript TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quran_student
    ON quran_attempts(LOWER(student_name));
CREATE INDEX IF NOT EXISTS idx_quran_surat
    ON quran_attempts(surat_id);
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


def save_hafalan_attempt(*, student_name, category, grade, item_id, item_title,
                          score, score_arab=None, score_artinya=None,
                          transcript_arab=None, transcript_artinya=None,
                          reference_arab=None, reference_artinya=None):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO hafalan_attempts
               (student_name, category, grade, item_id, item_title, score,
                score_arab, score_artinya, transcript_arab, transcript_artinya,
                reference_arab, reference_artinya)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                normalize_name(student_name),
                category,
                grade,
                item_id,
                item_title,
                int(score),
                int(score_arab) if score_arab is not None else None,
                int(score_artinya) if score_artinya is not None else None,
                transcript_arab,
                transcript_artinya,
                reference_arab,
                reference_artinya,
            ),
        )
        return cur.lastrowid


def get_hafalan_attempt(attempt_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM hafalan_attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
    return dict(row) if row else None


def hafalan_history(student_name, category=None, limit=100):
    sql = (
        "SELECT id, category, grade, item_id, item_title, score, score_arab, "
        "score_artinya, timestamp FROM hafalan_attempts "
        "WHERE LOWER(student_name) = ?"
    )
    params = [name_key(student_name)]
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def save_quran_attempt(*, student_name, surat_id, surat_nomor, surat_nama,
                        kategori, mode, jumlah_ayat, score,
                        score_per_ayat=None, transcript=None):
    import json as _json
    payload = (
        _json.dumps(score_per_ayat, ensure_ascii=False)
        if score_per_ayat is not None else None
    )
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO quran_attempts
               (student_name, surat_id, surat_nomor, surat_nama, kategori, mode,
                jumlah_ayat, score, score_per_ayat, transcript)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                normalize_name(student_name), surat_id, int(surat_nomor),
                surat_nama, kategori, mode, int(jumlah_ayat), int(score),
                payload, transcript,
            ),
        )
        return cur.lastrowid


def get_quran_attempt(attempt_id):
    import json as _json
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM quran_attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("score_per_ayat"):
        try:
            d["score_per_ayat"] = _json.loads(d["score_per_ayat"])
        except (ValueError, TypeError):
            d["score_per_ayat"] = None
    return d


def quran_history(student_name, limit=100):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, surat_id, surat_nomor, surat_nama, kategori, mode,
                      jumlah_ayat, score, timestamp
               FROM quran_attempts
               WHERE LOWER(student_name) = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (name_key(student_name), limit),
        ).fetchall()
    return [dict(r) for r in rows]


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
