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

### Kelas 6

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
| **Total Kelas 6** | **~985** |

### Kelas 2

| Mapel | Jumlah |
|---|---|
| Bahasa Inggris (Grammar Units 5–12) | 72 |

Cakupan Unit 5–12 mengikuti **grammar reference** buku siswa:

| Unit | Fokus grammar |
|---|---|
| 5 | Present Continuous (am/is/are + verb-ing, isn't/aren't, What ... doing?) |
| 6 | Polite Request (Can I have ..., please? — Here you are.) |
| 7 | Agreement (So do I / I don't) |
| 8 | Where + Prepositions of Place (behind / in front of / between, It's vs They're) |
| 9 | have/has got (kepemilikan) + Present Continuous untuk pakaian (is/are wearing) |
| 10 | like / love + Do/Does, doesn't, jawaban Yes/No |
| 11 | Object Pronouns (me/you/him/her/it/us/them) + Would you like ...? |
| 12 | want / wants + WH-Question (where / which) |

Soal Kelas 2 disimpan sebagai mata pelajaran terpisah dengan nama internal
"Bahasa Inggris Kelas 2" (label tampilan: "Bahasa Inggris" di bawah heading
"Kelas 2") sehingga **tidak tercampur** dengan "Bahasa Inggris" Kelas 6 di
database, leaderboard, maupun anti-repeat.

Untuk menambah mata pelajaran Kelas 2 (atau kelas lain) baru:

1. Buat file `questions/<key>.json` dengan schema yang sama.
2. Tambahkan entri ke `SUBJECTS` di `question_loader.py` dengan field
   `grade: "Kelas 2"` (atau nama kelas yang sesuai). Tambahkan
   `display_name` jika label UI berbeda dari `name` internal.
3. (Opsional) Tambahkan kelas baru ke `GRADE_ORDER` jika ingin urutan
   tertentu di landing page.

Untuk memvalidasi soal Kelas 2 English: `python validate_english_kelas2.py`.

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

## Modul Hafalan Doa & Hadits

Modul tambahan untuk **menguji hafalan** siswa terhadap 100 doa harian dan 100 hadits pilihan
(Grade 1–5). Berbeda dari modul sumatif, modul ini memakai **rekaman suara siswa** yang
ditranskripsi otomatis menggunakan Groq Whisper, lalu dibandingkan terhadap teks referensi.

**Filosofi tes hafalan murni**: di halaman praktik, **hanya nomor + judul** doa/hadits yang
ditampilkan. Teks Arab (dan artinya untuk hadits) sengaja **tidak ditampilkan** agar siswa
benar-benar menghafal dari memori. Teks lengkap baru muncul di halaman hasil sebagai feedback
edukatif.

### Mode pengujian

| Kategori | Tahapan rekam | Skor |
|---|---|---|
| Doa | 1 rekaman (bacaan Arab) | 0–100 |
| Hadits | 2 rekaman (Arab → artinya) | Skor Arab + Skor Artinya + Skor Akhir (60% Arab + 40% artinya) |

Ambang skor: ≥85 Sangat Baik · 70–84 Baik · 50–69 Cukup · <50 Perlu Latihan.

### Routes

| Route | Fungsi |
|---|---|
| `/hafalan/<category>` | Pilih grade (1–5 atau Semua) |
| `/hafalan/<category>/grade/<n>` | Daftar item + tombol Acak |
| `/hafalan/<category>/random?grade=<g>` | Acak 1 item |
| `/hafalan/<category>/item/<id>` | Halaman praktik (rekam suara) |
| `/hafalan/doa/<id>/submit` | Submit audio Arab (multipart) |
| `/hafalan/hadits/<id>/submit` | Submit dua audio (Arab + artinya) |
| `/hafalan/result/<attempt_id>` | Hasil + feedback |
| `/hafalan/riwayat` | Riwayat hafalan siswa |

### Konten (`content/doa.json` & `content/hadits.json`)

Saat ini SEMUA entry ditandai `"verified": false` karena PDF silabus sulit di-OCR dengan urutan
RTL yang benar. Teks Arab diisi dari versi standar kurikulum SD Islam Indonesia. **Perlu di-review
manual** sebelum dianggap final. Format:

```json
// doa.json
{ "id": "doa_001", "nomor": 1, "grade": 1, "judul": "...", "arab": "...", "verified": false }

// hadits.json
{ "id": "hadits_001", "nomor": 1, "grade": 1, "judul": "...",
  "arab": "...", "artinya": "...", "sumber": "HR. ...", "verified": false }
```

### Setup tambahan (lokal)

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env, isi GROQ_API_KEY = gsk_...
python app.py
```

Catatan dev lokal: `getUserMedia` (perekaman mic browser) hanya jalan di HTTPS atau di
`localhost`. Jangan gunakan IP LAN saat dev tanpa HTTPS.

### Deploy ke PythonAnywhere

1. Push branch ke GitHub repo yang sudah connected ke PA.
2. Di Bash console PA:
   ```bash
   cd ~/<folder-app>
   git pull
   workon <virtualenv>
   pip install -r requirements.txt
   ```
3. Web tab → **Environment variables**:
   - `GROQ_API_KEY = gsk_...`
4. **Whitelist check** (free tier PA hanya bisa hit domain whitelisted):
   ```bash
   curl -I https://api.groq.com
   ```
   - Kalau berhasil → lanjut Reload web app.
   - Kalau ditolak → request whitelist `api.groq.com` ke `forums@pythonanywhere.com`,
     atau upgrade ke Hacker plan ($5/bulan), atau fallback ke OpenAI Whisper API
     (sudah whitelisted; ganti `base_url` ke `https://api.openai.com/v1` di `transcriber.py`
     dan model ke `whisper-1`).
5. Reload web app.

### Privasi

Audio yang direkam siswa **dikirim ke server Groq** untuk transkripsi. Disclaimer kecil
sudah ditampilkan di footer halaman hafalan.

## Modul Hafalan Quran (Juz 30 & Al-Fatihah)

Modul ketiga untuk menguji hafalan **38 surat** (Al-Fatihah + 37 surat Juz 30). Filosofi
sama dengan modul Doa & Hadits: di halaman praktik hanya tampil **nomor + nama surat +
jumlah ayat**; teks ayat baru muncul di halaman hasil sebagai feedback edukatif.

### Mode rekaman

| Mode | Tersedia untuk | Output |
|---|---|---|
| Full-Surat (default) | Semua surat | 1 rekaman → 1 transkripsi → skor |
| Per-Ayat | Surat dengan >15 ayat | N rekaman (stepper) → skor per ayat + skor akhir (rata-rata) |

### Kategori panjang surat

| Slug | Range Ayat | Jumlah |
|---|---|---|
| `sangat-pendek` | ≤7 ayat | 13 |
| `pendek` | 8–15 ayat | 10 |
| `sedang` | 16–25 ayat | 8 |
| `panjang` | ≥26 ayat | 7 |
| `semua` | — | 38 |

### Toleransi khusus Quran

- **Bismillah opsional** untuk surat selain Al-Fatihah — siswa boleh mulai dengan/tanpa
  basmalah tanpa penalti.
- **Al-Fatihah** memerlukan basmalah sebagai ayat 1.
- **Alif wasla** (ٱ U+0671, sering dipakai di mushaf Uthmani) dinormalisasi ke alif biasa
  (ا) sebelum scoring.
- **Tajwid TIDAK dicek** — aplikasi hanya mengecek kebenaran teks bacaan. Disclaimer
  sudah ditampilkan di halaman praktik.

### Generate konten

Source: [risan/quran-json](https://github.com/risan/quran-json) (Uthmani script, harakat
lengkap). Generate ulang dengan:

```bash
python fetch_quran_data.py
# → menghasilkan content/juz30.json (38 surat lengkap)
```

Jalankan di dev environment saja, bukan di PythonAnywhere production.

### Routes

| Route | Fungsi |
|---|---|
| `/quran` | Pilih kategori panjang |
| `/quran/kategori/<slug>` | Daftar surat |
| `/quran/random?kategori=<slug>` | Acak 1 surat |
| `/quran/<surat_id>` | Praktik full-surat |
| `/quran/<surat_id>/ayat` | Praktik per-ayat (hanya >15 ayat) |
| `/quran/<surat_id>/submit` | Submit audio full |
| `/quran/<surat_id>/submit_ayat` | Submit N audio (multipart `audio_1...audio_N`) |
| `/quran/result/<attempt_id>` | Hasil + teks ayat |
| `/quran/riwayat` | Riwayat siswa |

## Pengembangan lanjutan

- Tambahkan diagram tren nilai per subject di profile (mis. via Chart.js CDN).
- Tambahkan ekspor PDF hasil attempt.
- Tambahkan import/export JSON untuk soal dari spreadsheet.
- Verifikasi manual semua teks Arab di `content/doa.json` & `content/hadits.json`, lalu ubah
  `"verified": true`.
