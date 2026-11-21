"""Tahap 1 — Ekstraksi (pertemuan X). Milik tim.

Baca setiap berkas di data/raw/ (CSV, JSON WebAPI BPS, XLSX BNPB, SDMX ILO, JSON WDI) menjadi
DataFrame mentah yang setia pada sumbernya: jangan membersihkan di sini, cukup ratakan struktur
dan catat asal tiap baris (`_berkas_raw` relatif data/raw/, `_sha256_raw` dari src.common.manifest).
"""

import pandas as pd

from src.common.manifest import RAW, baca
from src.common.hasil import tulis_hasil

from src.ekstraksi.pembaca_bps import (
    baca_bps_csv, baca_bps_json, ambil_berkas_bps_dari_manifest,
)
from src.ekstraksi.pembaca_wdi import baca_wdi_json
from src.ekstraksi.pembaca_ilostat import baca_ilostat_lengkap

NIM = "nim"


def _baca_semua_bps() -> pd.DataFrame:
    berkas = [b for b in ambil_berkas_bps_dari_manifest(baca(RAW))
              if b.endswith((".csv", ".json"))]
    if not berkas:
        raise FileNotFoundError("Tidak ada berkas BPS (.csv/.json) di manifest")
    daftar = []
    for b in berkas:
        df = baca_bps_csv(b) if b.endswith(".csv") else baca_bps_json(b)
        print(f"    {b}: {len(df)} baris")
        daftar.append(df)          # galat dibiarkan naik
    return pd.concat(daftar, ignore_index=True)


def jalankan(hasil_sebelumnya=None):
    print("--> Menjalankan pembaca BPS (CSV & JSON)...")
    df_bps = _baca_semua_bps()

    print("--> Menjalankan pembaca WDI...")
    df_wdi = baca_wdi_json()

    print("--> Menjalankan pembaca ILOSTAT...")
    df_ilostat = baca_ilostat_lengkap()

    df = pd.concat([df_bps, df_wdi, df_ilostat], ignore_index=True)
    assert df["_berkas_raw"].notna().all() and df["_sha256_raw"].notna().all()

    metrik = {
        "berkas_dibaca": int(df["_berkas_raw"].nunique()),
        "baris_mentah": int(len(df)),
        "format": 4,   # BPS csv, BPS json, WDI json, ILOSTAT SDMX-CSV
    }
    tulis_hasil(NIM, metrik)
    print(f"Berkas dibaca: {metrik['berkas_dibaca']}, baris mentah: {metrik['baris_mentah']}")
    return df