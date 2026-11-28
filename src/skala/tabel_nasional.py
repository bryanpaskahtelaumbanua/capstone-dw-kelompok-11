"""Tahap 6: Membuat tabel rekonsiliasi nasional dengan kategori selisih."""
from pathlib import Path
import pandas as pd
import numpy as np

SILVER = Path("data/silver/silver.parquet")
OUT = Path("results/124450007/tabel_nasional.csv")

def main():
    if not SILVER.exists():
        print(f"Silver belum ada: {SILVER}.")
        return

    df = pd.read_parquet(SILVER)
    
    # 1. Ambil baris Indonesia (BPS pakai 9999, WDI/ILO mungkin pakai IDN/Indonesia)
    is_nasional = (df["wilayah_kode"].astype(str) == "9999") | (df["wilayah_kode"].astype(str) == "IDN") | (df["nama_wilayah"] == "Indonesia")
    df_nas = df[is_nasional].copy()

    # 2. Bersihkan periode (kita ubah ke tahunan saja untuk rekonsiliasi)
    df_nas["tahun"] = df_nas["periode"].astype(str).str[:4]
    
    # 3. Pivot: baris = tahun, kolom = seri
    tabel = df_nas.pivot_table(index="tahun", columns="seri_kode", values="nilai", aggfunc="first")
    tabel.index.name = "periode"
    
    # 4. Hitung selisih (var543 - WDI ZS)
    if "var543" in tabel.columns and "SL.UEM.TOTL.ZS" in tabel.columns:
        tabel["selisih"] = tabel["var543"] - tabel["SL.UEM.TOTL.ZS"]
    else:
        tabel["selisih"] = np.nan
        
    # 5. Beri kategori (sederhana)
    def kategorikan(row):
        if pd.isna(row.get("var543")) or pd.isna(row.get("SL.UEM.TOTL.ZS")):
            return "tanpa pasangan"
        # Jika selisih sangat kecil, anggap sama (pembulatan)
        if abs(row["selisih"]) < 0.1:
            return "sama / pembulatan"
        # Jika ada nilai, kita kategorikan definisi berbeda (karena BPS vs ILO beda konsep)
        return "definisi berbeda"
        
    tabel["kategori"] = tabel.apply(kategorikan, axis=1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tabel.to_csv(OUT)
    
    # Hitung metrik
    total_pasangan = tabel["kategori"].value_counts().get("definisi berbeda", 0) + tabel["kategori"].value_counts().get("sama / pembulatan", 0)
    median_selisih = tabel["selisih"].median()
    
    print(f"Tabel nasional: {OUT} ({tabel.shape[0]} periode x {tabel.shape[1]} kolom)")
    print(f"Jumlah pasangan (beririsan): {total_pasangan}")
    print(f"Median selisih: {median_selisih:.4f}")

if __name__ == "__main__":
    main()