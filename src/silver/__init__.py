"""Tahap 2-4 - Profil, pembersihan, dan penyeragaman ke Silver (pertemuan II-VII).

Keluaran: data/silver/silver.parquet dengan skema minimal di src/common/skema.py.
Satu baris = satu seri x wilayah x periode x rincian x berkas sumber.
"""
from pathlib import Path
import pandas as pd
from src.common.manifest import RAW, baca

KOLOM_SILVER = [
    "sumber", "seri_kode", "wilayah_kode", "nama_wilayah",
    "periode", "jenis_periode", "rincian", "nilai",
    "satuan", "_berkas_raw", "_sha256_raw",
]


def _bersihkan_path_raw(path_str: str) -> str:
    p = str(path_str).replace("\\", "/")
    return p[4:] if p.startswith("raw/") else p


def _proses_bps(mentah: pd.DataFrame, manifest: dict) -> pd.DataFrame:
    if "var_id" not in mentah.columns:
        return pd.DataFrame(columns=KOLOM_SILVER)

    df = mentah[mentah["var_id"].notna()].copy()
    if df.empty:
        return pd.DataFrame(columns=KOLOM_SILVER)

    peta_periode = {
        191: ("tahun", lambda t: f"{int(t):04d}"),
        189: ("bulan", lambda t: f"{int(t):04d}-02"),
        190: ("bulan", lambda t: f"{int(t):04d}-08"),
    }

    jenis_list = []
    periode_list = []
    for pid, thn in zip(df["periode_id"].astype(int), df["tahun"].astype(int)):
        jenis, fmt = peta_periode[pid]
        jenis_list.append(jenis)
        periode_list.append(fmt(thn))

    berkas_clean = df["_berkas_raw"].map(_bersihkan_path_raw)
    out = pd.DataFrame({
        "sumber": "bps",
        "seri_kode": "var" + df["var_id"].astype(int).astype(str),
        "wilayah_kode": df["wilayah_id"].astype("int64"),
        "nama_wilayah": df["wilayah"].astype(str).str.strip(),
        "periode": periode_list,
        "jenis_periode": jenis_list,
        "rincian": "total",
        "nilai": pd.to_numeric(df["nilai"], errors="coerce"),
        "satuan": "persen",
        "_berkas_raw": berkas_clean,
        "_sha256_raw": berkas_clean.map(manifest),
    })
    return out.dropna(subset=["nilai"])


def _proses_wdi(mentah: pd.DataFrame, manifest: dict) -> pd.DataFrame:
    if "sumber" not in mentah.columns:
        return pd.DataFrame(columns=KOLOM_SILVER)

    df = mentah[mentah["sumber"] == "wdi"].copy()
    if df.empty:
        return pd.DataFrame(columns=KOLOM_SILVER)

    berkas_clean = df["_berkas_raw"].map(_bersihkan_path_raw)
    out = pd.DataFrame({
        "sumber": "wdi",
        "seri_kode": df["seri_kode"].astype(str).str.strip(),
        "wilayah_kode": pd.Series(9999, index=df.index, dtype="int64"),
        "nama_wilayah": "INDONESIA",
        "periode": df["periode"].astype(str).str.strip(),
        "jenis_periode": "tahun",
        "rincian": "total",
        "nilai": pd.to_numeric(df["nilai"], errors="coerce"),
        "satuan": "persen",
        "_berkas_raw": berkas_clean,
        "_sha256_raw": berkas_clean.map(manifest),
    })
    return out.dropna(subset=["nilai"])


def _proses_ilostat(manifest: dict) -> pd.DataFrame:
    target_series = ["SDG_0852_SEX_AGE_RT", "SDG_0852_SEX_DSB_RT", "UNE_DEAP_SEX_AGE_RT"]
    ilostat_dir = RAW / "ilostat"
    frames = []

    for path_csv in sorted(ilostat_dir.glob("**/*.csv")):
        rel_path = str(path_csv.relative_to(RAW)).replace("\\", "/")
        sha_val = manifest.get(rel_path)
        df_raw = pd.read_csv(path_csv, low_memory=False)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]

        raw_flow = df_raw["DATAFLOW"].astype(str)
        seri_clean = raw_flow.str.extract(r"DF_([A-Z0-9_]+)", expand=False).fillna(raw_flow)
        mask = seri_clean.isin(target_series)
        df_sub = df_raw[mask].copy()
        if df_sub.empty:
            continue

        seri_sub = seri_clean[mask]
        sex_col = df_sub["SEX"].astype(str).str.strip()
        if "AGE" in df_sub.columns:
            dim2_col = df_sub["AGE"].astype(str).str.strip()
        elif "DSB" in df_sub.columns:
            dim2_col = df_sub["DSB"].astype(str).str.strip()
        else:
            dim2_col = pd.Series("TOTAL", index=df_sub.index)

        rincian_col = sex_col + "|" + dim2_col
        freq_col = df_sub["FREQ"].astype(str).str.strip().str.upper()
        time_col = df_sub["TIME_PERIOD"].astype(str).str.strip()

        periode_fmt = []
        jenis_fmt = []
        for frq, tm in zip(freq_col, time_col):
            if frq == "Q" or "Q" in tm.upper():
                clean_q = tm.upper().replace("-", "")
                parts = clean_q.split("Q")
                periode_fmt.append(f"{parts[0]}-Q{parts[1]}")
                jenis_fmt.append("triwulan")
            else:
                periode_fmt.append(tm[:4])
                jenis_fmt.append("tahun")

        out = pd.DataFrame({
            "sumber": "ilostat",
            "seri_kode": seri_sub.values,
            "wilayah_kode": pd.Series(9999, index=df_sub.index, dtype="int64").values,
            "nama_wilayah": "INDONESIA",
            "periode": periode_fmt,
            "jenis_periode": jenis_fmt,
            "rincian": rincian_col.values,
            "nilai": pd.to_numeric(df_sub["OBS_VALUE"], errors="coerce").values,
            "satuan": "persen",
            "_berkas_raw": rel_path,
            "_sha256_raw": sha_val,
        })
        frames.append(out.dropna(subset=["nilai"]))

    if not frames:
        return pd.DataFrame(columns=KOLOM_SILVER)
    return pd.concat(frames, ignore_index=True)


def jalankan(mentah: pd.DataFrame) -> pd.DataFrame:
    """Terima keluaran tahap 1, tulis dan kembalikan DataFrame Silver."""
    manifest = baca(RAW)

    df_bps = _proses_bps(mentah, manifest)
    df_wdi = _proses_wdi(mentah, manifest)
    df_ilo = _proses_ilostat(manifest)

    silver_df = pd.concat([df_bps, df_wdi, df_ilo], ignore_index=True)
    silver_df = silver_df[KOLOM_SILVER].copy()
    silver_df["wilayah_kode"] = silver_df["wilayah_kode"].astype("int64")
    silver_df["nilai"] = silver_df["nilai"].astype("float64")

    kunci = ["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"]
    silver_df = silver_df.drop_duplicates(subset=kunci, keep="last").reset_index(drop=True)

    out_path = RAW.parent / "silver" / "silver.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    silver_df.to_parquet(out_path, index=False)
    print(f"Silver tersimpan di {out_path} ({len(silver_df):,} baris)")
    return silver_df
