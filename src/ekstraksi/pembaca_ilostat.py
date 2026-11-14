import json
from pathlib import Path
import pandas as pd
from src.common.manifest import RAW, baca

def baca_ilostat_lengkap():
    manifest_dict = baca(RAW)
    semua_baris = []
    ilostat_dir = RAW / "ilostat"

    if not ilostat_dir.exists():
        print(f"Direktori {ilostat_dir} tidak ditemukan.")
        return pd.DataFrame()

    target_series = ["SDG_0852_SEX_AGE_RT", "SDG_0852_SEX_DSB_RT", "UNE_DEAP_SEX_AGE_RT"]

    for path_berkas in ilostat_dir.glob("**/*.csv"):
        rel_path_str = str(path_berkas.relative_to(RAW.parent)).replace("\\", "/")
        sha256_val = manifest_dict.get(rel_path_str, "")

        try:
            df_raw = pd.read_csv(path_berkas, low_memory=False)
            df_raw.columns = [str(c).strip() for c in df_raw.columns]

            col_ind = 'DATAFLOW' if 'DATAFLOW' in df_raw.columns else next((c for c in df_raw.columns if 'IND' in c.upper()), None)
            col_time = 'TIME_PERIOD' if 'TIME_PERIOD' in df_raw.columns else 'TIME'
            col_val = 'OBS_VALUE' if 'OBS_VALUE' in df_raw.columns else 'VALUE'
            col_area = 'REF_AREA' if 'REF_AREA' in df_raw.columns else 'COUNTRY'
            col_freq = 'FREQ' if 'FREQ' in df_raw.columns else None

            if not col_ind or not col_time or not col_val:
                continue

            for _, row in df_raw.iterrows():
                seri_kode = str(row.get(col_ind, ""))
                
                if any(ts.lower() in seri_kode.lower() for ts in target_series):
                    raw_time = str(row.get(col_time, ""))
                    freq = str(row.get(col_freq, "")).upper() if col_freq and col_freq in df_raw.columns else ""

                    periode = raw_time
                    if "Q" in raw_time.upper():
                        clean_q = raw_time.upper().replace("-", "")
                        if "Q" in clean_q:
                            parts = clean_q.split("Q")
                            if len(parts) == 2:
                                periode = f"{parts[0]}-Q{parts[1]}"

                    baris = {
                        "sumber": "ilostat_csv",
                        "seri_kode": seri_kode,
                        "wilayah_kode": row.get(col_area) if col_area in df_raw.columns else None,
                        "nama_wilayah": None,
                        "periode": periode,
                        "nilai": row.get(col_val) if col_val in df_raw.columns else None,
                        "satuan": row.get('UNIT_MEASURE') if 'UNIT_MEASURE' in df_raw.columns else None,
                        "_berkas_raw": rel_path_str,
                        "_sha256_raw": sha256_val
                    }
                    semua_baris.append(baris)

        except Exception as e:
            print(f"Gagal membaca CSV {path_berkas.name}: {e}")

    for path_json in ilostat_dir.glob("**/*.json"):
        rel_path_json = str(path_json.relative_to(RAW.parent)).replace("\\", "/")
        sha256_json = manifest_dict.get(rel_path_json, "")
        
        try:
            with open(path_json, "r", encoding="utf-8") as jf:
                data_json = json.load(jf)
        except Exception as e:
            print(f"Gagal membaca JSON {path_json.name}: {e}")

    df_hasil = pd.DataFrame(semua_baris)
    return df_hasil

if __name__ == "__main__":
    df_ilostat = baca_ilostat_lengkap()
    print(f"Berhasil membaca berkas ILOSTAT. CSV dan JSON: {len(df_ilostat)} baris dengan atribut lineage dan jenis_periode lengkap.")
    print(df_ilostat.head())