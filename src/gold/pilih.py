"""Aturan satu nilai per sel Gold untuk seri utama var543 level provinsi (Tahap 4, Kartu #25).

Tahap 1 (ATURAN): saring baris yang bukan bagian panel; tiap penolakan dicatat per alasan.
Tahap 2 (snapshot): bila satu sel punya beberapa baris terpilih, menang berturut-turut:
  snapshot terbaru -> format kanonik (csv sebelum json) -> urutan nama berkas.
  Baris yang kalah dicatat sebagai tidak terpilih; bila nilainya berbeda ditandai revisi.
Periode: hanya YYYY (tahunan), YYYY-02 (Februari), YYYY-08 (Agustus); tidak dirata-ratakan.
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
    ("periode_bukan_feb_agu_tahunan",
     lambda s: s["periode"].astype(str).str.fullmatch(r"\d{4}(-(02|08))?")),
]
ALASAN_SNAPSHOT = ["snapshot_lebih_lama", "format_non_kanonik", "urutan_nama_berkas"]
SEMUA_ALASAN = [a for a, _ in ATURAN] + ALASAN_SNAPSHOT
RANK_FORMAT = {"csv": 0, "json": 1}
KUNCI_SEL = ["wilayah_kode", "periode", "seri_kode", "rincian"]


def _info_berkas(s: pd.DataFrame) -> pd.DataFrame:
    path = s["_berkas_raw"].astype(str)
    return pd.DataFrame({
        "_snap": path.str.extract(r"(\d{4}-\d{2}-\d{2})")[0].fillna(""),
        "_fmt": path.str.extract(r"\.([A-Za-z0-9]+)$")[0].str.lower().map(RANK_FORMAT).fillna(9),
        "_nama": path,
    }, index=s.index)


def pilih_satu_nilai(silver: pd.DataFrame, aturan=ATURAN):
    """Kembalikan (terpilih, tidak_terpilih, ringkasan).

    terpilih membawa _posisi_silver (posisi baris di Silver, 0..n-1) dan tanpa sel ganda.
    tidak_terpilih membawa kolom alasan (+ nilai_berbeda untuk yang kalah snapshot).
    ringkasan: jumlah per alasan, semua aturan tercantum (termasuk 0).
    """
    s = silver.reset_index(drop=True).copy()
    s["_posisi_silver"] = np.arange(len(s))

    # Tahap 1: aturan penyaring, alasan = aturan pertama yang dilanggar
    alasan = pd.Series("", index=s.index, dtype=object)
    for nama, lolos in aturan:
        alasan[(alasan == "") & ~lolos(s).astype(bool)] = nama
    lolos_saring = s[alasan == ""].copy()
    tidak = s[alasan != ""].copy()
    tidak["alasan"] = alasan[alasan != ""]
    tidak["nilai_berbeda"] = False

    # Tahap 2: satu nilai per sel (snapshot -> format -> nama berkas)
    t = pd.concat([lolos_saring, _info_berkas(lolos_saring)], axis=1)
    t = t.sort_values(["_snap", "_fmt", "_nama"], ascending=[False, True, True], kind="stable")
    t["_urut"] = t.groupby(KUNCI_SEL, sort=False).cumcount()
    menang = t[t["_urut"] == 0]
    kalah = t[t["_urut"] > 0].copy()
    if len(kalah):
        w = menang.set_index(KUNCI_SEL)[["_snap", "_fmt", "_nama", "nilai"]]
        w = w.rename(columns=lambda c: "w_" + c.lstrip("_"))
        kal = kalah.join(w, on=KUNCI_SEL)
        kalah["alasan"] = np.where(kal["_snap"] != kal["w_snap"], "snapshot_lebih_lama",
                          np.where(kal["_fmt"] != kal["w_fmt"], "format_non_kanonik",
                                   "urutan_nama_berkas"))
        kalah["nilai_berbeda"] = ((kal["nilai"] != kal["w_nilai"])
                                  & ~(kal["nilai"].isna() & kal["w_nilai"].isna())).values
        tidak = pd.concat([tidak, kalah], ignore_index=False)

    bantu = ["_snap", "_fmt", "_nama", "_urut"]
    terpilih = menang.drop(columns=bantu).sort_values("_posisi_silver")
    tidak = tidak.drop(columns=[c for c in bantu if c in tidak.columns])

    sem = SEMUA_ALASAN + [a for a in tidak["alasan"].unique() if a not in SEMUA_ALASAN]
    ringkasan = pd.DataFrame({"alasan": sem})
    ringkasan["jumlah_baris"] = ringkasan["alasan"].map(tidak["alasan"].value_counts()).fillna(0).astype(int)
    ringkasan["nilai_berbeda_revisi"] = ringkasan["alasan"].map(
        tidak.groupby("alasan")["nilai_berbeda"].sum()).fillna(0).astype(int)
    return terpilih, tidak, ringkasan


def simpan(terpilih, tidak, ringkasan, gold_dir: Path = DEFAULT_GOLD_DIR) -> Path:
    """Tulis ringkasan pemilihan: jumlah tak-terpilih per aturan, untuk log keputusan."""
    gold_dir.mkdir(parents=True, exist_ok=True)
    out = gold_dir / "ringkasan_pemilihan.csv"
    atas = pd.DataFrame({"alasan": ["terpilih"], "jumlah_baris": [len(terpilih)], "nilai_berbeda_revisi": [0]})
    pd.concat([atas, ringkasan], ignore_index=True).to_csv(out, index=False)
    return out
