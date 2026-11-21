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
from src.ekstraksi.pembaca_wdi import baca_wdi_json, baca_wdi_metadata
from src.ekstraksi.pembaca_ilostat import baca_ilostat_lengkap, baca_ilostat_json_semua

NIM = "124450003"


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

    print("--> Menjalankan pembaca WDI (data dan metadata)...")
    df_wdi = baca_wdi_json()
    df_wdi_meta = baca_wdi_metadata()

    print("--> Menjalankan pembaca ILOSTAT (CSV, DSD, metadata)...")
    df_ilostat = baca_ilostat_lengkap()
    df_ilo_json = baca_ilostat_json_semua()

    # tabel pengamatan; metadata dan DSD punya kolom lain, jadi tidak ikut concat
    # tabel pengamatan; metadata dan DSD punya kolom lain, jadi tidak ikut concat
    df = pd.concat([df_bps, df_wdi, df_ilostat], ignore_index=True)
    semua = [df, df_wdi_meta, df_ilo_json]
    for t in semua:
        assert t["_berkas_raw"].notna().all() and t["_sha256_raw"].notna().all()

    n_berkas = int(sum(t["_berkas_raw"].nunique() for t in semua))
    n_baris = int(len(df))                                          # hanya pengamatan
    n_meta = int(len(df_wdi_meta) + len(df_ilo_json))               # metadata dan DSD
    metrik = {
        "berkas_dibaca": n_berkas,
        "baris_mentah": n_baris,
        "baris_metadata": n_meta,
        "format": 5,   # BPS csv, BPS json, WDI json, ILOSTAT sdmx-csv, ILOSTAT json
    }
    tulis_hasil(NIM, metrik)
    print(f"Berkas dibaca: {n_berkas}, baris mentah (pengamatan): {n_baris}, baris metadata: {n_meta}")
    return df