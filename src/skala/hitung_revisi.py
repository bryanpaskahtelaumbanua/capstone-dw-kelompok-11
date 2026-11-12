"""Hitung besaran revisi antarrilis dari wdi_revisi.csv."""
from pathlib import Path
import pandas as pd

IN = Path("results/124450007/wdi_revisi.csv")
OUT = Path("results/124450007/wdi_revisi_ringkas.csv")


def main():
    df = pd.read_csv(IN, dtype={"rilis": str})
    df["rilis_int"] = df["rilis"].astype(int)
    df = df.sort_values(["seri", "periode", "rilis_int"])
    
    # Hitung selisih nilai dengan rilis sebelumnya untuk periode yang sama
    df["nilai_sebelum"] = df.groupby(["seri", "periode"])["nilai"].shift(1)
    df["revisi"] = (df["nilai"] - df["nilai_sebelum"]).abs()
    rev = df.dropna(subset=["revisi"])

    ringkas = (
        rev.groupby("seri")["revisi"]
        .agg(jumlah_revisi="count", revisi_median="median", revisi_maks="max")
        .reset_index()
    )
    
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ringkas.to_csv(OUT, index=False)
    print(ringkas.to_string(index=False))


if __name__ == "__main__":
    main()