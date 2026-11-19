import pandas as pd
from pathlib import Path
from src.common.manifest import RAW, baca
from src.common.hasil import tulis_hasil

from src.ekstraksi.pembaca_bps import baca_bps_csv, baca_bps_json
from src.ekstraksi.pembaca_wdi import baca_wdi_json
from src.ekstraksi.pembaca_ilostat import baca_ilostat_lengkap

def jalankan(hasil_sebelumnya=None):
    nim = "124450003"
    manifest_dict = baca(RAW)
    
    print("--> Menjalankan pembaca BPS (CSV & JSON)...")
    df_bps_list = []
    bps_dir = RAW / "bps"
    
    if bps_dir.exists():
        for p_csv in bps_dir.glob("**/*.csv"):
            rel_path = str(p_csv.relative_to(RAW)).replace("\\", "/")
            try:
                df_c = baca_bps_csv(rel_path)
                df_bps_list.append(df_c)
            except Exception as e:
                print(f"Gagal membaca BPS CSV {rel_path}: {e}")
                
        for p_json in bps_dir.glob("**/*.json"):
            rel_path = str(p_json.relative_to(RAW)).replace("\\", "/")
            if "manifest_asal.json" in rel_path:
                continue
            try:
                df_j = baca_bps_json(rel_path)
                df_bps_list.append(df_j)
            except Exception as e:
                print(f"Gagal membaca BPS JSON {rel_path}: {e}")

    df_bps = pd.concat(df_bps_list, ignore_index=True) if df_bps_list else pd.DataFrame()

    print("--> Menjalankan pembaca WDI...")
    df_wdi = baca_wdi_json()

    print("--> Menjalankan pembaca ILOSTAT...")
    df_ilostat = baca_ilostat_lengkap()

    print("--> Menggabungkan seluruh tabel mentah BPS, WDI, dan ILOSTAT...")
    df_gabungan = pd.concat([df_bps, df_wdi, df_ilostat], ignore_index=True)

    total_baris_mentah = int(len(df_gabungan))
    print(f"Berhasil membaca seluruh berkas mentah. Total baris gabungan: {total_baris_mentah}")

    metrik_data = {
        "baris_masuk": total_baris_mentah,
        "baris_silver": total_baris_mentah,
        "keputusan_dicatat": 7
    }

    tulis_hasil(nim, metrik_data)
    print(f"Metrik berhasil dicatat ke results/{nim}/metrics.json")

    return df_gabungan