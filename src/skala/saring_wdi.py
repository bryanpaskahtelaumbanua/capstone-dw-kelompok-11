"""Tahap 7: baca arsip WDI, saring 2 seri Indonesia, simpan tabel."""
import json
import re
import tarfile
from pathlib import Path

import pandas as pd

ARSIP_DIR = Path("data/raw/wdi_arsip/2026-10-20/versi")
SERI = {"SL.UEM.TOTL.ZS", "SL.UEM.TOTL.NE.ZS"}
OUT = Path("results/124450007/wdi_revisi.csv")


def baca_satu_tar(path_tar: Path):
    rilis = path_tar.name.replace(".tar.gz", "")
    baris = []
    
    with tarfile.open(path_tar) as t:
        for m in t.getmembers():
            if not m.isfile() or not m.name.endswith(".json"):
                continue
            try:
                obj = json.loads(t.extractfile(m).read())
            except json.JSONDecodeError:
                continue
                
            for obs in obj.get("source", {}).get("data", []):
                var = obs.get("variable", [])
                d_id = {v["concept"]: v.get("id") for v in var}
                d_val = {v["concept"]: v.get("value") for v in var}
                
                # Filter Country: IDN (id) atau Indonesia (value)
                if d_id.get("Country") != "IDN" and d_val.get("Country") != "Indonesia":
                    continue
                    
                # Filter Series: harus dari field 'id'
                if d_id.get("Series") not in SERI:
                    continue
                    
                # Ambil tahun dari field Time
                waktu = d_val.get("Time") or d_id.get("Time") or ""
                mth = re.search(r"(\d{4})", waktu)
                if not mth:
                    continue
                    
                baris.append({
                    "rilis": rilis,
                    "periode": int(mth.group(1)),
                    "seri": d_id["Series"],
                    "nilai": obs.get("value"),
                })
                
    return baris


def main():
    semua = []
    # Membaca seluruh 142 file tar.gz
    for path_tar in sorted(ARSIP_DIR.glob("*.tar.gz")):
        semua.extend(baca_satu_tar(path_tar))
        
    df = pd.DataFrame(semua)
    if df.empty:
        print("Tidak ada baris; cek nama seri / struktur arsip.")
        return
        
    # Buang nilai yang kosong (None)
    df = df.dropna(subset=["nilai"])
    
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    
    print(f"Rilis dibaca: {df['rilis'].nunique()}")
    print(f"Baris: {len(df)}")
    print("Jumlah rilis per seri:")
    print(df.groupby("seri")["rilis"].nunique())
    print("Rentang periode per seri:")
    print(df.groupby("seri")["periode"].agg(["min", "max"]))


if __name__ == "__main__":
    main()