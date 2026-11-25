import os
import pandas as pd


def _muat_dataframe(sumber_data) -> pd.DataFrame | None:
    if sumber_data is None:
        return None
    if isinstance(sumber_data, pd.DataFrame):
        return sumber_data
    if isinstance(sumber_data, str) and os.path.exists(sumber_data):
        if sumber_data.endswith(".parquet"):
            return pd.read_parquet(sumber_data)
        if sumber_data.endswith(".csv"):
            return pd.read_csv(sumber_data)
    return None


def validasi_silver(df: pd.DataFrame) -> dict:
    """
    Aturan validasi dasar tabel Silver (Kasus 11 - Pengangguran Terbuka).
    """
    aturan_total = 0
    aturan_lolos = 0
    error_log = []

    # 1. Kelengkapan 11 kolom wajib Silver
    aturan_total += 1
    kolom_wajib = [
        "sumber", "seri_kode", "wilayah_kode", "nama_wilayah",
        "periode", "jenis_periode", "rincian", "nilai",
        "satuan", "_berkas_raw", "_sha256_raw"
    ]
    kolom_hilang = [k for k in kolom_wajib if k not in df.columns]
    if not kolom_hilang:
        aturan_lolos += 1
    else:
        raise ValueError(f"[ATURAN 1 GAGAL] Kolom wajib Silver hilang: {kolom_hilang}")

    # 2. Rentang nilai 0-100 dan tidak kosong
    aturan_total += 1
    nilai_invalid = df[df["nilai"].isna() | (df["nilai"] < 0) | (df["nilai"] > 100)]
    if nilai_invalid.empty:
        aturan_lolos += 1
    else:
        error_log.append(
            f"[ATURAN 2 GAGAL] {len(nilai_invalid)} baris memiliki nilai di luar rentang 0-100 atau NaN."
        )

    # 3. Kesesuaian jenis_periode dan format periode (termasuk triwulan ILO)
    aturan_total += 1
    salah_tahun = df[
        (df["jenis_periode"] == "tahun")
        & (~df["periode"].astype(str).str.match(r"^\d{4}$"))
    ]
    salah_triwulan = df[
        (df["jenis_periode"] == "triwulan")
        & (~df["periode"].astype(str).str.match(r"^\d{4}-Q[1-4]$"))
    ]
    salah_bulan = df[
        (df["jenis_periode"] == "bulan")
        & (~df["periode"].astype(str).str.match(r"^\d{4}-(0[1-9]|1[0-2])$"))
    ]
    salah_semester = df[
        (df["jenis_periode"] == "semester")
        & (~df["periode"].astype(str).str.match(r"^\d{4}-S[1-2]$"))
    ]
    jenis_tak_dikenal = df[
        ~df["jenis_periode"].isin(["tahun", "triwulan", "bulan", "semester"])
    ]

    total_salah_periode = (
        len(salah_tahun)
        + len(salah_triwulan)
        + len(salah_bulan)
        + len(salah_semester)
        + len(jenis_tak_dikenal)
    )
    if total_salah_periode == 0:
        aturan_lolos += 1
    else:
        error_log.append(
            f"[ATURAN 3 GAGAL] {total_salah_periode} baris memiliki format periode tidak sesuai jenis_periode."
        )

    # 4. Keunikan kunci Silver
    aturan_total += 1
    kunci_unik = [
        "sumber", "seri_kode", "wilayah_kode",
        "periode", "jenis_periode", "rincian", "_berkas_raw"
    ]
    duplikat = df[df.duplicated(subset=kunci_unik, keep=False)]
    if duplikat.empty:
        aturan_lolos += 1
    else:
        error_log.append(
            f"[ATURAN 4 GAGAL] {len(duplikat)} baris duplikat pada kunci unik Silver."
        )

    # 5. Konsistensi satuan per seri_kode (tidak boleh bersatuan ganda & wajib 'persen')
    aturan_total += 1
    satuan_per_seri = df.groupby("seri_kode")["satuan"].nunique()
    seri_ganda_satuan = satuan_per_seri[satuan_per_seri > 1]
    satuan_bukan_persen = df[df["satuan"].astype(str).str.lower() != "persen"]

    if seri_ganda_satuan.empty and satuan_bukan_persen.empty:
        aturan_lolos += 1
    else:
        error_log.append(
            f"[ATURAN 5 GAGAL] Satuan tidak konsisten (seri satuan ganda: {list(seri_ganda_satuan.index)}, non-persen: {len(satuan_bukan_persen)} baris)."
        )

    if error_log:
        raise ValueError("Validasi Silver Gagal:\n" + "\n".join(error_log))

    print(f"  [Validasi Silver] LOLOS {aturan_lolos}/{aturan_total} aturan ({len(df)} baris).")
    return {
        "aturan_validasi": aturan_total,
        "aturan_lolos": aturan_lolos,
        "baris_silver_divalidasi": len(df),
    }


def jalankan(silver_data=None, gold_data=None) -> dict:
    """
    Entrypoint resmi yang dipanggil oleh pipeline.py:
    validasi.jalankan(h["silver"], h["gold"])
    """
    ringkasan = {
        "aturan_validasi": 0,
        "aturan_lolos": 0,
    }

    df_silver = _muat_dataframe(silver_data)
    if df_silver is None:
        df_silver = _muat_dataframe("data/silver/silver.parquet")

    if df_silver is not None and not df_silver.empty:
        res_silver = validasi_silver(df_silver)
        ringkasan["aturan_validasi"] += res_silver["aturan_validasi"]
        ringkasan["aturan_lolos"] += res_silver["aturan_lolos"]

    # Validasi tambahan untuk Gold (Sprint 2-3): rincian umur ILO tidak tumpang tindih
    df_gold = _muat_dataframe(gold_data)
    if df_gold is not None and not df_gold.empty:
        if {"sumber", "wilayah_kode", "periode", "rincian"}.issubset(df_gold.columns):
            ringkasan["aturan_validasi"] += 1
            df_ilo = df_gold[df_gold["sumber"].astype(str).str.upper().str.contains("ILO")]
            kelompok_induk = {"total", "15+", "15-64", "25+"}
            for (wil, per), grup in df_ilo.groupby(["wilayah_kode", "periode"]):
                rincian_set = set(grup["rincian"].astype(str).str.lower())
                if len(rincian_set.intersection(kelompok_induk)) > 0 and len(rincian_set) > 1:
                    raise ValueError(
                        f"[VALIDASI GOLD GAGAL] Kelompok umur ILO tumpang tindih pada wilayah {wil}, periode {per}: {rincian_set}"
                    )
            ringkasan["aturan_lolos"] += 1

    return ringkasan
