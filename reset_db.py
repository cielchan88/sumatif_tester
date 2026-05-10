"""Reset all stored data: attempts, leaderboard, seen_questions.

Usage:
    python reset_db.py            # reset everything
    python reset_db.py --seen     # reset only seen_questions
    python reset_db.py --student "Nama"   # reset all data for one student
"""
import argparse
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "exam.db")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seen", action="store_true", help="Reset only seen_questions")
    parser.add_argument("--student", help="Reset only this student's data (case-insensitive)")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print("No database file at", DB_PATH)
        return

    with sqlite3.connect(DB_PATH) as conn:
        if args.student:
            key = args.student.strip().lower()
            cur = conn.execute(
                "SELECT id FROM attempts WHERE LOWER(student_name)=?", (key,)
            ).fetchall()
            ids = [r[0] for r in cur]
            if ids:
                qmarks = ",".join("?" * len(ids))
                conn.execute(f"DELETE FROM attempt_answers WHERE attempt_id IN ({qmarks})", ids)
            conn.execute("DELETE FROM attempts WHERE LOWER(student_name)=?", (key,))
            conn.execute("DELETE FROM seen_questions WHERE LOWER(student_name)=?", (key,))
            print(f"Cleared data for student '{args.student}'.")
        elif args.seen:
            conn.execute("DELETE FROM seen_questions")
            print("Cleared seen_questions.")
        else:
            conn.execute("DELETE FROM attempt_answers")
            conn.execute("DELETE FROM attempts")
            conn.execute("DELETE FROM seen_questions")
            print("Cleared attempts, attempt_answers, and seen_questions.")


if __name__ == "__main__":
    main()
