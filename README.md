# Sumatif Tester — Latihan Asesmen Sumatif Kelas 6

Aplikasi web latihan ujian sumatif untuk siswa kelas 6 SD (SD Nabawi Islamic School, TA 2025/2026). 40 soal pilihan ganda per sesi, timer 60 menit, scoring otomatis, leaderboard, profil siswa, dan **anti-repeat** sehingga siswa jarang bertemu soal yang sama berulang.

## Setup

Butuh Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Buka `http://localhost:5000` di browser.

Database SQLite (`data/exam.db`) dibuat otomatis saat pertama kali dijalankan.

## Struktur folder

```
sumatif_tester/
├── app.py                  # Routes Flask
├── models.py               # Skema SQLite + helpers
├── question_loader.py      # Loader JSON + sampling anti-repeat
├── reset_db.py             # Skrip reset database
├── requirements.txt
├── static/
│   ├── css/style.css
│   └── js/exam.js          # Timer, navigasi, autosave
├── templates/              # base, landing, exam, result, leaderboard, profile, attempt_review
├── questions/              # 9 file JSON soal (per mapel)
└── data/exam.db            # auto-created
```

## Menambah / mengedit soal

Setiap mapel memiliki file JSON terpisah di folder `questions/`. Format:

```json
{
  "subject": "Pendidikan Agama Islam",
  "questions": [
    {
      "id": 1,
      "topic": "Khulafaur Rasyidin",
      "difficulty": "easy|medium|hard",
      "question": "Pertanyaan...",
      "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "correct_answer": "A",
      "explanation": "Penjelasan singkat 1–2 kalimat."
    }
  ]
}
```

Saran:
- Pastikan `id` unik dalam satu file (urutan tidak harus berurutan, tetapi unik).
- Distribusi `difficulty` dijaga sekitar 40% easy / 40% medium / 20% hard agar attempt seimbang.
- `topic` dipakai oleh halaman result untuk breakdown.

Setelah mengedit JSON, restart `python app.py` agar perubahan terbaca.

## Volume soal saat ini

| Mapel | Jumlah |
|---|---|
| Pendidikan Agama Islam | 130 |
| Pendidikan Pancasila | 104 |
| Bahasa Indonesia | 193 |
| Bahasa Inggris | 112 |
| Matematika | 104 |
| IPA (English) | 105 |
| IPS | 111 |
| PJOK | 83 |
| SBDP | 103 |
| **Total** | **~985** |

## Reset data

Berikut skenario reset yang biasa diperlukan:

```bash
# Reset semua: leaderboard, riwayat attempt, dan seen_questions
python reset_db.py

# Reset hanya catatan soal yang sudah pernah dilihat (anti-repeat di-reset)
python reset_db.py --seen

# Reset semua data milik siswa tertentu (case-insensitive)
python reset_db.py --student "Ahmad Faruq"

# Atau cara paling kasar: hapus file db, akan dibuat ulang
rm data/exam.db
```

## Catatan arsitektur

- **Flask + SQLite + Bootstrap 5** (tanpa ORM atau framework JS berat).
- **Anti-repeat**: setiap kali siswa menyelesaikan attempt, semua soal yang muncul tercatat di tabel `seen_questions` (komposit `student_name+subject+question_id`). Saat attempt baru dimulai, sampling diprioritaskan dari subset *unseen*. Jika unseen < 30, sisanya diisi soal yang **paling lama tidak dilihat** (least-recently-seen). Jika seluruh pool sudah seen, penanda direset dan banner ditampilkan.
- **Distribusi difficulty**: target 40/40/20 (easy/medium/hard) dipertahankan saat sampling.
- **Acak opsi**: posisi A/B/C/D diacak per attempt; `correct_answer` ikut menyesuaikan.
- **State exam** disimpan di Flask session sehingga refresh browser tidak menghilangkan progress.
- **Auto-submit**: timer mencapai 00:00 → submit otomatis.
- **Leaderboard**: ranking memakai *best score* per kombinasi siswa+subject (tidak inflated).
- **Profile**: identifikasi case-insensitive (anggap nama unik dalam keluarga; tanpa login).

## Deploy ke PythonAnywhere (gratis)

Lihat panduan ringkas di komentar `wsgi_pythonanywhere_template.py`. Catatan penting:

- Jangan jalankan dengan `debug=True` di production (sudah dimatikan secara default — hanya aktif kalau env `FLASK_DEBUG=1`).
- Set env `SUMATIF_SECRET` di file WSGI PythonAnywhere agar session tetap valid setelah restart.
- File `data/exam.db` persist otomatis di disk PythonAnywhere — tidak perlu volume tambahan.

## Pengembangan lanjutan

- Tambahkan diagram tren nilai per subject di profile (mis. via Chart.js CDN).
- Tambahkan ekspor PDF hasil attempt.
- Tambahkan import/export JSON untuk soal dari spreadsheet.
