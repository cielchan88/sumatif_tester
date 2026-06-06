"""Sumatif Tester — Flask app for 6th-grade exam practice."""
import os
import secrets
import time
from datetime import datetime

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_session import Session

import hafalan_loader as hl
import models
import question_loader as ql
import quran_loader as qln
import quran_scorer as qs
import scorer

app = Flask(__name__)
app.secret_key = os.environ.get("SUMATIF_SECRET", secrets.token_hex(32))

# Server-side sessions: the exam state (40 questions + answers) easily exceeds
# the 4 KB cookie limit, so we store it on disk and only put a session ID in
# the cookie.
SESSION_DIR = os.path.join(os.path.dirname(__file__), "data", "flask_session")
os.makedirs(SESSION_DIR, exist_ok=True)
app.config.update(
    SESSION_TYPE="filesystem",
    SESSION_FILE_DIR=SESSION_DIR,
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
)
Session(app)

EXAM_SECONDS = 60 * 60  # 60 minutes


@app.before_request
def _ensure_db():
    if not getattr(app, "_db_ready", False):
        models.init_db()
        app._db_ready = True


@app.route("/")
def landing():
    return render_template(
        "landing.html",
        subject_groups=ql.subjects_by_grade(),
        student_name=session.get("student_name", ""),
    )


@app.route("/start", methods=["POST"])
def start_exam():
    name = (request.form.get("student_name") or "").strip()
    subject = request.form.get("subject", "").strip()
    if not name or subject not in ql.SUBJECT_BY_NAME:
        return redirect(url_for("landing"))

    questions, status = ql.sample_questions(name, subject, n=40)
    if not questions:
        return redirect(url_for("landing"))

    session["student_name"] = name
    session["subject"] = subject
    session["questions"] = questions
    session["answers"] = {}
    session["flags"] = {}
    session["start_time"] = int(time.time())
    session["pool_status"] = status
    session["current_idx"] = 0
    session.modified = True
    return redirect(url_for("exam"))


@app.route("/exam")
def exam():
    if "questions" not in session:
        return redirect(url_for("landing"))
    elapsed = int(time.time()) - session.get("start_time", int(time.time()))
    remaining = max(0, EXAM_SECONDS - elapsed)
    if remaining == 0:
        return redirect(url_for("submit_exam"))
    return render_template(
        "exam.html",
        questions=session["questions"],
        answers=session.get("answers", {}),
        flags=session.get("flags", {}),
        student_name=session.get("student_name"),
        subject=session.get("subject"),
        remaining=remaining,
        total_seconds=EXAM_SECONDS,
        pool_status=session.get("pool_status"),
        current_idx=session.get("current_idx", 0),
    )


@app.route("/exam/save", methods=["POST"])
def save_answer():
    if "questions" not in session:
        return {"ok": False}, 400
    data = request.get_json(silent=True) or {}
    qid = str(data.get("question_id"))
    answer = data.get("answer")
    flagged = data.get("flagged")
    current_idx = data.get("current_idx")

    answers = session.get("answers", {})
    flags = session.get("flags", {})
    if answer in ("A", "B", "C", "D"):
        answers[qid] = answer
    elif answer is None and qid in answers:
        # explicit clear
        if data.get("clear"):
            answers.pop(qid, None)
    if flagged is not None:
        if flagged:
            flags[qid] = True
        else:
            flags.pop(qid, None)
    if isinstance(current_idx, int):
        session["current_idx"] = current_idx
    session["answers"] = answers
    session["flags"] = flags
    session.modified = True
    return {"ok": True}


@app.route("/exam/submit", methods=["POST", "GET"])
def submit_exam():
    if "questions" not in session:
        return redirect(url_for("landing"))

    questions = session["questions"]
    answers = session.get("answers", {})
    student_name = session["student_name"]
    subject = session["subject"]
    start_time = session.get("start_time", int(time.time()))
    time_used = min(EXAM_SECONDS, int(time.time()) - start_time)

    correct = 0
    wrong = 0
    blank = 0
    answer_records = []
    review_items = []
    for q in questions:
        student_ans = answers.get(str(q["id"]))
        is_correct = student_ans == q["correct_answer"]
        if student_ans is None:
            blank += 1
        elif is_correct:
            correct += 1
        else:
            wrong += 1
        answer_records.append(
            {
                "question_id": q["id"],
                "student_answer": student_ans,
                "correct_answer": q["correct_answer"],
                "is_correct": is_correct,
            }
        )
        review_items.append(
            {
                "question": q,
                "student_answer": student_ans,
                "is_correct": is_correct,
            }
        )

    score = round((correct / len(questions)) * 100, 2) if questions else 0.0
    attempt_id = models.save_attempt(
        student_name, subject, score, correct, wrong, blank, time_used, answer_records
    )

    # Topic breakdown
    by_topic = {}
    for item in review_items:
        topic = item["question"].get("topic", "Lainnya")
        bucket = by_topic.setdefault(topic, {"total": 0, "correct": 0})
        bucket["total"] += 1
        if item["is_correct"]:
            bucket["correct"] += 1

    # Clear exam state but keep student_name
    for k in ("questions", "answers", "flags", "start_time", "subject", "pool_status", "current_idx"):
        session.pop(k, None)
    session.modified = True

    return render_template(
        "result.html",
        score=score,
        correct=correct,
        wrong=wrong,
        blank=blank,
        time_used=time_used,
        review=review_items,
        student_name=student_name,
        subject=subject,
        by_topic=by_topic,
        attempt_id=attempt_id,
    )


@app.route("/leaderboard")
def leaderboard():
    subject = request.args.get("subject") or ql.SUBJECTS[0]["name"]
    if subject not in ql.SUBJECT_BY_NAME:
        subject = ql.SUBJECTS[0]["name"]
    rows = models.leaderboard(subject)
    stats = models.subject_stats(subject)
    student_name = session.get("student_name", "")
    student_rank = None
    if student_name:
        key = student_name.strip().lower()
        for i, r in enumerate(rows, start=1):
            if r["student_name"].strip().lower() == key:
                student_rank = (i, r)
                break
    return render_template(
        "leaderboard.html",
        subject=subject,
        rows=rows[:10],
        all_rows=rows,
        stats=stats,
        student_rank=student_rank,
        subjects=ql.SUBJECTS,
        student_name=student_name,
    )


@app.route("/profile")
def profile():
    name = request.args.get("name") or session.get("student_name", "")
    name = name.strip()
    if not name:
        return redirect(url_for("landing"))
    attempts = models.student_attempts(name)
    by_subject = models.student_subject_summary(name)
    # Augment with pool size and seen progress
    enriched = []
    for s in by_subject:
        size = ql.pool_size(s["subject"])
        seen = len(models.get_seen_question_ids(name, s["subject"]))
        s = dict(s)
        s["pool_size"] = size
        s["seen_count"] = seen
        enriched.append(s)
    overall = {
        "total_attempts": len(attempts),
        "avg_score": (sum(a["score"] for a in attempts) / len(attempts)) if attempts else 0,
    }
    best_subject = max(enriched, key=lambda r: r["avg_score"]) if enriched else None
    worst_subject = min(enriched, key=lambda r: r["avg_score"]) if enriched else None
    return render_template(
        "profile.html",
        student_name=name,
        attempts=attempts,
        per_subject=enriched,
        overall=overall,
        best_subject=best_subject,
        worst_subject=worst_subject,
    )


@app.route("/profile/attempt/<int:attempt_id>")
def attempt_review(attempt_id):
    attempt, answers = models.attempt_detail(attempt_id)
    if not attempt:
        abort(404)
    items = []
    for a in answers:
        q = ql.find_question(attempt["subject"], a["question_id"])
        if not q:
            continue
        items.append(
            {
                "question": q,
                "student_answer": a["student_answer"],
                "is_correct": bool(a["is_correct"]),
            }
        )
    return render_template(
        "attempt_review.html",
        attempt=attempt,
        items=items,
    )


# ---------------------------------------------------------------------------
# Hafalan (Doa & Hadits) module
# ---------------------------------------------------------------------------

GRADE_LABELS = {1: "Grade 1", 2: "Grade 2", 3: "Grade 3", 4: "Grade 4", 5: "Grade 5"}


def _require_category(category):
    if category not in hl.CATEGORIES:
        abort(404)
    return hl.CATEGORIES[category]


@app.route("/hafalan/<category>")
def hafalan_grade(category):
    meta = _require_category(category)
    counts = hl.grade_counts(category)
    return render_template(
        "hafalan_grade.html",
        category=category,
        category_meta=meta,
        counts=counts,
        student_name=session.get("student_name", ""),
    )


@app.route("/hafalan/<category>/set_name", methods=["POST"])
def hafalan_set_name(category):
    _require_category(category)
    name = (request.form.get("student_name") or "").strip()
    if name:
        session["student_name"] = name
        session.modified = True
    return redirect(request.referrer or url_for("hafalan_grade", category=category))


@app.route("/hafalan/<category>/grade/<int:grade>")
def hafalan_select(category, grade):
    meta = _require_category(category)
    if grade not in (0, 1, 2, 3, 4, 5):
        abort(404)
    items = hl.items_by_grade(category, grade)
    return render_template(
        "hafalan_select.html",
        category=category,
        category_meta=meta,
        grade=grade,
        grade_label="Semua Grade" if grade == 0 else GRADE_LABELS[grade],
        items=items,
        student_name=session.get("student_name", ""),
    )


@app.route("/hafalan/<category>/random")
def hafalan_random(category):
    _require_category(category)
    try:
        grade = int(request.args.get("grade", 0))
    except (TypeError, ValueError):
        grade = 0
    item = hl.random_item(category, grade)
    if not item:
        return redirect(url_for("hafalan_grade", category=category))
    return redirect(url_for("hafalan_practice", category=category, item_id=item["id"]))


@app.route("/hafalan/<category>/item/<item_id>")
def hafalan_practice(category, item_id):
    meta = _require_category(category)
    item = hl.find_item(category, item_id)
    if not item:
        abort(404)
    if not session.get("student_name"):
        return redirect(url_for("hafalan_grade", category=category))
    template = (
        "hafalan_doa_practice.html"
        if category == "doa"
        else "hafalan_hadits_practice.html"
    )
    return render_template(
        template,
        category=category,
        category_meta=meta,
        item=item,
        student_name=session["student_name"],
    )


def _read_audio(field):
    f = request.files.get(field)
    if not f:
        return None
    data = f.read()
    return data if data else None


@app.route("/hafalan/doa/<item_id>/submit", methods=["POST"])
def hafalan_doa_submit(item_id):
    item = hl.find_item("doa", item_id)
    if not item:
        return jsonify({"ok": False, "error": "Doa tidak ditemukan."}), 404
    student_name = session.get("student_name")
    if not student_name:
        return jsonify({"ok": False, "error": "Nama siswa belum diisi."}), 400
    audio = _read_audio("audio")
    if not audio:
        return jsonify({"ok": False, "error": "Audio tidak terkirim."}), 400

    try:
        import transcriber
        transcript = transcriber.transcribe(audio, language="ar")
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "Gagal memproses suara. Coba lagi ya.",
            "detail": str(e),
        }), 502

    result = scorer.score_doa(item["arab"], transcript)
    attempt_id = models.save_hafalan_attempt(
        student_name=student_name,
        category="doa",
        grade=item["grade"],
        item_id=item["id"],
        item_title=item["judul"],
        score=result["score"],
        transcript_arab=transcript,
        reference_arab=item["arab"],
    )
    return jsonify({
        "ok": True,
        "result_url": url_for("hafalan_result", attempt_id=attempt_id),
    })


@app.route("/hafalan/hadits/<item_id>/submit", methods=["POST"])
def hafalan_hadits_submit(item_id):
    item = hl.find_item("hadits", item_id)
    if not item:
        return jsonify({"ok": False, "error": "Hadits tidak ditemukan."}), 404
    student_name = session.get("student_name")
    if not student_name:
        return jsonify({"ok": False, "error": "Nama siswa belum diisi."}), 400
    audio_arab = _read_audio("audio_arab")
    audio_artinya = _read_audio("audio_artinya")
    if not audio_arab or not audio_artinya:
        return jsonify({"ok": False, "error": "Audio belum lengkap."}), 400

    try:
        import transcriber
        hyp_arab = transcriber.transcribe(audio_arab, language="ar",
                                           filename="arab.webm")
        hyp_artinya = transcriber.transcribe(audio_artinya, language="id",
                                              filename="artinya.webm")
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "Gagal memproses suara. Coba lagi ya.",
            "detail": str(e),
        }), 502

    result = scorer.score_hadits(
        item["arab"], item["artinya"], hyp_arab, hyp_artinya
    )
    attempt_id = models.save_hafalan_attempt(
        student_name=student_name,
        category="hadits",
        grade=item["grade"],
        item_id=item["id"],
        item_title=item["judul"],
        score=result["score"],
        score_arab=result["score_arab"],
        score_artinya=result["score_artinya"],
        transcript_arab=hyp_arab,
        transcript_artinya=hyp_artinya,
        reference_arab=item["arab"],
        reference_artinya=item["artinya"],
    )
    return jsonify({
        "ok": True,
        "result_url": url_for("hafalan_result", attempt_id=attempt_id),
    })


@app.route("/hafalan/result/<int:attempt_id>")
def hafalan_result(attempt_id):
    attempt = models.get_hafalan_attempt(attempt_id)
    if not attempt:
        abort(404)
    item = hl.find_item(attempt["category"], attempt["item_id"])
    feedback = scorer.feedback_for(attempt["score"])
    tip = ""
    if attempt["category"] == "hadits":
        tip = scorer.hadits_tip(
            attempt.get("score_arab") or 0,
            attempt.get("score_artinya") or 0,
        )
    prev_item, next_item, position, total = hl.neighbors(
        attempt["category"], attempt["grade"], attempt["item_id"]
    )
    return render_template(
        "hafalan_result.html",
        attempt=attempt,
        item=item,
        category=attempt["category"],
        category_meta=hl.CATEGORIES.get(attempt["category"], {}),
        feedback=feedback,
        tip=tip,
        student_name=session.get("student_name", attempt["student_name"]),
        prev_item=prev_item,
        next_item=next_item,
        position=position,
        total=total,
    )


@app.route("/hafalan/riwayat")
def hafalan_riwayat():
    # Redirect to the unified riwayat (legacy URL).
    category = request.args.get("category")
    args = {}
    if category in ("doa", "hadits"):
        args["kind"] = category
    name = request.args.get("name")
    if name:
        args["name"] = name
    return redirect(url_for("riwayat", **args))


# ---------------------------------------------------------------------------
# Hafalan Quran (Juz 30 + Al-Fatihah)
# ---------------------------------------------------------------------------

@app.route("/quran")
def quran_select():
    return render_template(
        "quran_select.html",
        items=qln.all_surat_sorted(),
        student_name=session.get("student_name", ""),
    )


@app.route("/quran/set_name", methods=["POST"])
def quran_set_name():
    name = (request.form.get("student_name") or "").strip()
    if name:
        session["student_name"] = name
        session.modified = True
    return redirect(request.referrer or url_for("quran_select"))


@app.route("/quran/random")
def quran_random():
    surat = qln.random_surat()
    if not surat:
        return redirect(url_for("quran_select"))
    return redirect(url_for("quran_practice", surat_id=surat["id"]))


@app.route("/quran/<surat_id>")
def quran_practice(surat_id):
    surat = qln.find(surat_id)
    if not surat:
        abort(404)
    if not session.get("student_name"):
        return redirect(url_for("quran_select"))
    return render_template(
        "quran_practice.html",
        surat=surat,
        student_name=session["student_name"],
        ayat_mode_available=surat["jumlah_ayat"] > 15,
    )


@app.route("/quran/<surat_id>/ayat")
def quran_practice_ayat(surat_id):
    surat = qln.find(surat_id)
    if not surat:
        abort(404)
    if surat["jumlah_ayat"] <= 15:
        return redirect(url_for("quran_practice", surat_id=surat_id))
    if not session.get("student_name"):
        return redirect(url_for("quran_select"))
    return render_template(
        "quran_practice_ayat.html",
        surat=surat,
        student_name=session["student_name"],
    )


def _surat_full_text(surat):
    return " ".join(a["arab"] for a in surat["ayat"])


@app.route("/quran/<surat_id>/submit", methods=["POST"])
def quran_submit(surat_id):
    surat = qln.find(surat_id)
    if not surat:
        return jsonify({"ok": False, "error": "Surat tidak ditemukan."}), 404
    student_name = session.get("student_name")
    if not student_name:
        return jsonify({"ok": False, "error": "Nama siswa belum diisi."}), 400
    audio = _read_audio("audio")
    if not audio:
        return jsonify({"ok": False, "error": "Audio tidak terkirim."}), 400

    try:
        import transcriber
        transcript = transcriber.transcribe(audio, language="ar")
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "Gagal memproses suara. Coba lagi ya.",
            "detail": str(e),
        }), 502

    is_fatihah = surat["nomor"] == 1
    result = qs.score_full_surat(_surat_full_text(surat), transcript,
                                  is_al_fatihah=is_fatihah)
    attempt_id = models.save_quran_attempt(
        student_name=student_name, surat_id=surat["id"],
        surat_nomor=surat["nomor"], surat_nama=surat["nama_latin"],
        kategori=surat["kategori"], mode="full",
        jumlah_ayat=surat["jumlah_ayat"], score=result["score"],
        transcript=transcript,
    )
    return jsonify({
        "ok": True,
        "result_url": url_for("quran_result", attempt_id=attempt_id),
    })


@app.route("/quran/<surat_id>/submit_ayat", methods=["POST"])
def quran_submit_ayat(surat_id):
    surat = qln.find(surat_id)
    if not surat:
        return jsonify({"ok": False, "error": "Surat tidak ditemukan."}), 404
    if surat["jumlah_ayat"] <= 15:
        return jsonify({"ok": False, "error": "Mode per-ayat tidak tersedia untuk surat ini."}), 400
    student_name = session.get("student_name")
    if not student_name:
        return jsonify({"ok": False, "error": "Nama siswa belum diisi."}), 400

    n = surat["jumlah_ayat"]
    hyp_list = []
    try:
        import transcriber
        for i in range(1, n + 1):
            audio = _read_audio(f"audio_{i}")
            if not audio:
                return jsonify({"ok": False,
                                "error": f"Audio ayat {i} belum terkirim."}), 400
            text = transcriber.transcribe(audio, language="ar",
                                           filename=f"ayat_{i}.webm")
            hyp_list.append(text)
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "Gagal memproses suara. Coba lagi ya.",
            "detail": str(e),
        }), 502

    ref_list = [a["arab"] for a in surat["ayat"]]
    result = qs.score_per_ayat(ref_list, hyp_list)
    if "error" in result:
        return jsonify({"ok": False, "error": "Jumlah ayat tidak cocok."}), 400

    attempt_id = models.save_quran_attempt(
        student_name=student_name, surat_id=surat["id"],
        surat_nomor=surat["nomor"], surat_nama=surat["nama_latin"],
        kategori=surat["kategori"], mode="per_ayat",
        jumlah_ayat=surat["jumlah_ayat"], score=result["score"],
        score_per_ayat=result["ayat"],
        transcript=" \n".join(hyp_list),
    )
    return jsonify({
        "ok": True,
        "result_url": url_for("quran_result", attempt_id=attempt_id),
    })


@app.route("/quran/result/<int:attempt_id>")
def quran_result(attempt_id):
    attempt = models.get_quran_attempt(attempt_id)
    if not attempt:
        abort(404)
    surat = qln.find(attempt["surat_id"])
    feedback = scorer.feedback_for(attempt["score"])
    prev_s, next_s, position, total = qln.neighbors(attempt["surat_id"])
    return render_template(
        "quran_result.html",
        attempt=attempt,
        surat=surat,
        feedback=feedback,
        prev_surat=prev_s,
        next_surat=next_s,
        position=position,
        total=total,
        student_name=session.get("student_name", attempt["student_name"]),
    )


@app.route("/quran/riwayat")
def quran_riwayat():
    # Redirect to the unified riwayat (legacy URL).
    args = {"kind": "quran"}
    name = request.args.get("name")
    if name:
        args["name"] = name
    return redirect(url_for("riwayat", **args))


@app.route("/riwayat")
def riwayat():
    name = (request.args.get("name") or session.get("student_name") or "").strip()
    if not name:
        return redirect(url_for("landing"))
    kind = request.args.get("kind") or None
    if kind not in ("doa", "hadits", "quran", None):
        kind = None
    rows = models.unified_hafalan_history(name, category=kind)
    return render_template(
        "riwayat.html",
        student_name=name,
        rows=rows,
        kind=kind,
    )


@app.template_filter("fmttime")
def fmttime(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


@app.template_filter("fmtdate")
def fmtdate(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", ""))
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return str(value)


if __name__ == "__main__":
    models.init_db()
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
