"""Pembentukan panel Gold provinsi x periode x indikator dari Silver (Tahap 4, Kartu #26)."""
from pathlib import Path
import pandas as pd 
from src.gold.pilih import ATURAN, pilih_satu_nilai

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD_DIR = ROOT / "data" / "gold"
PROFIL_ANOMALI_PATH = ROOT / "reports" / "profil" / "anomali_terklasifikasi_var543.csv"

PETA_PERIODE_PROFIL = {
    "Tahunan": lambda thn: f"{int(thn):04d}",
    "Februari": lambda thn: f"{int(thn):04d}-02",
    "Agustus": lambda thn: f"{int(thn):04d}-08",
}


def pilih_sel_gold(silver: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Aturan satu nilai per sel Gold; aturan lengkap ada di src/gold/pilih.py (ATURAN).

    Mengembalikan baris Silver terpilih (kolom dan urutan Silver tetap) dan jumlah baris yang tidak terpilih.
    """
    terpilih, tidak, _ = pilih_satu_nilai(silver, ATURAN)
    if terpilih.empty:
        raise ValueError("Tidak ada baris var543 level provinsi yang lolos aturan pemilihan Gold.")
    asli = silver.iloc[sorted(terpilih["_posisi_silver"].tolist())].copy()
    return asli, int(len(tidak))


def _muat_penanda_anomali(path_anomali: Path = PROFIL_ANOMALI_PATH) -> pd.DataFrame:
    """Baca penanda outlier/patahan dari hasil profil Sprint 1 untuk diteruskan ke Gold."""
    if not path_anomali.exists():
        raise FileNotFoundError(f"Penanda anomali tidak ditemukan: {path_anomali}. Gold tidak boleh diam-diam memakai 'normal'.")

    df_anom = pd.read_csv(path_anomali)
    periode_fmt = [
        PETA_PERIODE_PROFIL[str(p).strip()](t)
        for p, t in zip(df_anom["periode"], df_anom["tahun"])
    ]
    out = pd.DataFrame({
        "wilayah_kode": df_anom["wilayah_id"].astype("int64"),
        "periode": periode_fmt,
        "status_anomali": df_anom["kategori"].astype(str).str.strip(),
    })
    return out.drop_duplicates(subset=["wilayah_kode", "periode"], keep="first")


def bangun_panel_gold(silver: pd.DataFrame, out_dir: Path = DEFAULT_GOLD_DIR) -> pd.DataFrame:
    """Reshape Silver terpilih menjadi panel Gold (provinsi x periode x indikator)."""
    terpilih, _ = pilih_sel_gold(silver)

    terpilih["indikator"] = terpilih["seri_kode"] + "_" + terpilih["rincian"]

    # Wajib memakai .pivot() (bukan pivot_table) agar berhenti dengan galat bila ada sel ganda
    panel = (
        terpilih.pivot(
            index=["wilayah_kode", "nama_wilayah", "periode"],
            columns="indikator",
            values="nilai",
        )
        .reset_index()
    )
    panel.columns.name = None

    # Ketelusuran (lineage) setiap sel Gold ke baris Silver asalnya
    jejak = (
        terpilih[["wilayah_kode", "periode", "_berkas_raw", "_sha256_raw"]]
        .drop_duplicates(subset=["wilayah_kode", "periode"])
    )
    panel = panel.merge(jejak, on=["wilayah_kode", "periode"], how="left", validate="one_to_one")

    # Teruskan penanda outlier/patahan dari Sprint 1 tanpa mengubah nilai asli
    penanda = _muat_penanda_anomali()
    if not penanda.empty:
        panel = panel.merge(penanda, on=["wilayah_kode", "periode"], how="left", validate="one_to_one")
        panel["status_anomali"] = panel["status_anomali"].fillna("normal")
    else:
        panel["status_anomali"] = "normal"

    panel = panel.sort_values(["wilayah_kode", "periode"]).reset_index(drop=True)
    panel["wilayah_kode"] = panel["wilayah_kode"].astype("int64")
    panel["var543_total"] = panel["var543_total"].astype("float64")

    kolom_urut = [
        "wilayah_kode",
        "nama_wilayah",
        "periode",
        "var543_total",
        "status_anomali",
        "_berkas_raw",
        "_sha256_raw",
    ]
    panel = panel[kolom_urut]

    if panel.duplicated(subset=["wilayah_kode", "periode"]).any():
        raise ValueError("Kunci panel Gold (wilayah_kode, periode) tidak unik!")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "panel.parquet"
    panel.to_parquet(out_path, index=False)
    print(f"Panel Gold tersimpan di {out_path} ({len(panel):,} baris, {panel['wilayah_kode'].nunique()} provinsi)")
    return panel
