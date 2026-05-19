"""Run once to generate content/juz30.json.

Fetches Al-Fatihah (1) + Juz 30 surat (78–114) from risan/quran-json on GitHub.
The dataset is the Uthmani script with full harakat.

NOTE: Run this in your dev environment, not on PythonAnywhere. The output JSON
is what gets committed to the repo and served to students.
"""
import json
from pathlib import Path
from urllib.request import urlopen

SOURCE_URL = (
    "https://raw.githubusercontent.com/risan/quran-json/main/dist/quran.json"
)
OUTPUT = Path(__file__).parent / "content" / "juz30.json"
SURAT_NUMBERS = [1] + list(range(78, 115))  # Al-Fatihah + Juz 30 (37 surat)

ARTI_NAMA = {
    1: "Pembukaan",
    78: "Berita Besar",
    79: "Malaikat-Malaikat Yang Mencabut",
    80: "Ia Bermuka Masam",
    81: "Menggulung",
    82: "Terbelah",
    83: "Orang-Orang Yang Curang",
    84: "Terbelah",
    85: "Gugusan Bintang",
    86: "Yang Datang di Malam Hari",
    87: "Yang Paling Tinggi",
    88: "Hari Pembalasan",
    89: "Fajar",
    90: "Negeri",
    91: "Matahari",
    92: "Malam",
    93: "Waktu Duha",
    94: "Melapangkan",
    95: "Buah Tin",
    96: "Segumpal Darah",
    97: "Kemuliaan",
    98: "Bukti",
    99: "Kegoncangan",
    100: "Berlari Kencang",
    101: "Hari Kiamat",
    102: "Bermegah-Megahan",
    103: "Masa",
    104: "Pengumpat",
    105: "Gajah",
    106: "Suku Quraisy",
    107: "Barang-Barang Yang Berguna",
    108: "Nikmat Yang Banyak",
    109: "Orang-Orang Kafir",
    110: "Pertolongan",
    111: "Gejolak Api",
    112: "Memurnikan Keesaan Allah",
    113: "Waktu Subuh",
    114: "Umat Manusia",
}


def categorize(ayat_count: int) -> str:
    if ayat_count <= 7:
        return "sangat-pendek"
    if ayat_count <= 15:
        return "pendek"
    if ayat_count <= 25:
        return "sedang"
    return "panjang"


def main():
    print(f"Fetching from {SOURCE_URL} …")
    with urlopen(SOURCE_URL, timeout=20) as r:
        all_surat = json.loads(r.read().decode("utf-8"))
    by_num = {s["id"]: s for s in all_surat}

    out = []
    for num in SURAT_NUMBERS:
        src = by_num.get(num)
        if not src:
            raise RuntimeError(f"Surat {num} not found in source")
        ayat = [
            {"nomor": a["id"], "arab": a["text"]}
            for a in src["verses"]
        ]
        out.append({
            "id": f"{num:03d}",
            "nomor": num,
            "nama_arab": src["name"],
            "nama_latin": src["transliteration"],
            "arti": ARTI_NAMA.get(num, ""),
            "jumlah_ayat": src["total_verses"],
            "kategori": categorize(src["total_verses"]),
            "ayat": ayat,
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved {len(out)} surat to {OUTPUT}")
    print(f"Categories: {dict((k, sum(1 for s in out if s['kategori']==k)) for k in ('sangat-pendek','pendek','sedang','panjang'))}")


if __name__ == "__main__":
    main()
