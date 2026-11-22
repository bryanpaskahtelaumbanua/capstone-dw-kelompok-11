"""Tahap 1 — Ekstraksi (pertemuan X). Milik tim.

Baca setiap berkas di data/raw/ (CSV, JSON WebAPI BPS, SDMX ILO, JSON WDI) menjadi DataFrame
mentah yang setia pada sumbernya: tidak ada pembersihan, hanya meratakan struktur dan mencatat
asal tiap baris (`_berkas_raw`, `_sha256_raw`). Setiap berkas di MANIFEST harus terbaca.
"""
import pandas as pd

from src.common.manifest import RAW, baca
from src.ekstraksi import pembaca_bps as bps
from src.ekstraksi import pembaca_ilostat as ilo
from src.ekstraksi import pembaca_wdi as wdi


def ekstrak() -> dict:
    manifest = baca(RAW)
    laporan, pengamatan, metadata = [], [], []

    def catat(rel, jenis, df, rekaman=None):
        if len(df):
            assert df["_berkas_raw"].eq(rel).all(), f"{rel}: _berkas_raw tidak sama dengan path"
            assert df["_sha256_raw"].notna().all(), f"{rel}: ada _sha256_raw kosong"
            assert df["_sha256_raw"].eq(manifest[rel]).all(), f"{rel}: sha256 tak cocok dengan MANIFEST"
            (pengamatan if jenis == "pengamatan" else metadata).append(df)
        laporan.append({"berkas": rel, "jenis": jenis,
                        "rekaman": len(df) if rekaman is None else rekaman, "baris": len(df)})

    for b in bps.ambil_berkas_bps_dari_manifest(manifest):
        catat(b, "pengamatan", bps.baca_bps_csv(b) if b.endswith(".csv") else bps.baca_bps_json(b))
    for b in bps.berkas_bps_metadata(manifest):
        catat(b, "metadata", bps.baca_bps_metadata(b))
    for b in wdi.berkas_wdi_dari_manifest(manifest):
        df, n = wdi.baca_wdi_berkas(b)
        catat(b, "pengamatan" if "/data/" in b else "metadata", df, n)
    for b in ilo.berkas_ilostat(manifest, ".csv", "data"):
        catat(b, "pengamatan", ilo.baca_ilostat_csv(b))
    for b in ilo.berkas_ilostat(manifest, ".json"):
        catat(b, "metadata", ilo.baca_ilostat_json(b))

    # pencocokan dengan MANIFEST: tidak boleh ada yang terlewat atau asing
    dibaca = {r["berkas"] for r in laporan}
    terlewat, asing = sorted(set(manifest) - dibaca), sorted(dibaca - set(manifest))
    if terlewat or asing:
        raise RuntimeError(f"Berkas manifest terlewat: {terlewat}; berkas di luar manifest: {asing}")

    df = pd.concat(pengamatan, ignore_index=True)
    metrik = {
        "berkas_dibaca": len(laporan),
        "baris_mentah": int(len(df)),                      # hanya pengamatan
        "baris_metadata": int(sum(len(t) for t in metadata)),
        "format": 5,   # BPS csv, BPS json, WDI json, ILOSTAT sdmx-csv, ILOSTAT json
    }
    return {"pengamatan": df, "laporan": pd.DataFrame(laporan), "metrik": metrik,
            "n_manifest": len(manifest)}


def cetak_laporan(r: dict) -> None:
    print(r["laporan"].to_string(index=False))
    m = r["metrik"]
    print(f"Pencocokan manifest: {m['berkas_dibaca']} dari {r['n_manifest']} berkas terbaca, "
          f"hash setiap baris sama dengan MANIFEST")
    print(f"Berkas dibaca: {m['berkas_dibaca']}, baris mentah (pengamatan): {m['baris_mentah']}, "
          f"baris metadata: {m['baris_metadata']}")


def jalankan(hasil_sebelumnya=None):
    r = ekstrak()
    cetak_laporan(r)
    return r["pengamatan"]