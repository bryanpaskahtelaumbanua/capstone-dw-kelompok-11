"""Aturan satu nilai per sel Gold untuk seri utama var543 level provinsi (Tahap 4, Kartu #26).

Setiap aturan: (alasan_tidak_terpilih, fungsi yang True bila baris LOLOS aturan).
Aturan diperiksa berurutan; baris yang gagal dicatat pada aturan pertama yang dilanggar.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD_DIR = ROOT / "data" / "gold"

ATURAN = [
    ("bukan_seri_var543", lambda s: s["seri_kode"] == "var543"),
    ("baris_nasional_wilayah_9999", lambda s: s["wilayah_kode"] != 9999),
    ("rincian_bukan_total", lambda s: s["rincian"] == "total"),
    ("satuan_bukan_persen", lambda s: s["satuan"] == "persen"),
]
KUNCI_SEL = ["wilayah_kode", "periode", "seri_kode", "rincian"]


def pilih_satu_nilai(silver: pd.DataFrame, aturan=ATURAN):
    """Kembalikan (terpilih, tidak_terpilih, ringkasan).

    terpilih membawa kolom _posisi_silver (posisi baris di Silver, 0..n-1).
    tidak_terpilih membawa kolom alasan. ringkasan: jumlah per alasan.
    """
    s = silver.reset_index(drop=True).copy()
    s["_posisi_silver"] = np.arange(len(s))
    alasan = pd.Series("", index=s.index, dtype=object)
    for nama, lolos in aturan:
        gagal = (alasan == "") & ~lolos(s)
        alasan[gagal] = nama

    terpilih = s[alasan == ""].copy()
    tidak = s[alasan != ""].copy()
    tidak["alasan"] = alasan[alasan != ""]

    duplikat = int(terpilih.duplicated(subset=KUNCI_SEL).sum())
    if duplikat > 0:
        raise ValueError(f"Ditemukan {duplikat} sel ganda sebelum pivot Gold pada var543.")

    ringkasan = (
        tidak["alasan"].value_counts().rename_axis("alasan").reset_index(name="jumlah_baris")
        if len(tidak) else pd.DataFrame({"alasan": [], "jumlah_baris": []})
    )
    return terpilih, tidak, ringkasan


def simpan(terpilih, tidak, ringkasan, gold_dir: Path = DEFAULT_GOLD_DIR) -> Path:
    """Tulis ringkasan pemilihan (jumlah tak-terpilih per alasan) untuk log keputusan."""
    gold_dir.mkdir(parents=True, exist_ok=True)
    out = gold_dir / "ringkasan_pemilihan.csv"
    baris = pd.concat(
        [pd.DataFrame({"alasan": ["terpilih"], "jumlah_baris": [len(terpilih)]}), ringkasan],
        ignore_index=True,
    )
    baris.to_csv(out, index=False)
    return out
