import json
from pathlib import Path
import pandas as pd
from src.common.manifest import RAW, baca

def baca_wdi_json(target_indicators=None):
    if target_indicators is None:
        target_indicators = ["SL.UEM.TOTL.ZS", "SL.UEM.TOTL.NE.ZS"]

    manifest_dict = baca(RAW)
    semua_baris = []

    for path_berkas in Path(RAW / "wdi").glob("**/*.json"):
        rel_path_str = str(path_berkas.relative_to(RAW.parent)).replace("\\", "/")
        
        sha256_val = manifest_dict.get(rel_path_str)
        if not sha256_val:
            matching_keys = [k for k in manifest_dict.keys() if path_berkas.name in k]
            if matching_keys:
                sha256_val = manifest_dict[matching_keys[0]]
                rel_path_str = matching_keys[0]

        try:
            with open(path_berkas, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            records = data[1] if isinstance(data, list) and len(data) > 1 else data.get("data", [])

            for item in records:
                ind_obj = item.get("indicator", {})
                ind_id = ind_obj.get("id") if isinstance(ind_obj, dict) else None

                if ind_id in target_indicators:
                    country_obj = item.get("country", {})
                    baris = {
                        "sumber": "wdi",
                        "seri_kode": ind_id,
                        "wilayah_kode": country_obj.get("id"),
                        "nama_wilayah": country_obj.get("value"),
                        "periode": item.get("date"),
                        "nilai": item.get("value"),
                        "satuan": None,
                        "_berkas_raw": rel_path_str,
                        "_sha256_raw": sha256_val
                    }
                    semua_baris.append(baris)
        except Exception as e:
            print(f"Gagal membaca {path_berkas}: {e}")

    df_hasil = pd.DataFrame(semua_baris)
    return df_hasil

if __name__ == "__main__":
    df_wdi = baca_wdi_json()
    print(f"Total baris terbaca: {len(df_wdi)}")
    print(df_wdi[['seri_kode', 'periode', 'nilai', '_berkas_raw', '_sha256_raw']].head())