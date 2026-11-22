"""Tahap 6 (persiapan): tabel nasional periode x seri dari Silver."""
from pathlib import Path
import pandas as pd

SILVER = Path("data/silver/silver.parquet")
OUT = Path("results/124450007/tabel_nasional.csv")

SERI = {
    "var543",
    "SL.UEM.TOTL.ZS",
    "SL.UEM.TOTL.NE.ZS",
    "SDG_0852_SEX_AGE_RT",
}


def main():
    if not SILVER.exists():
        print(f"Silver belum ada: {SILVER}. Menunggu komponen Ekstraksi.")
        return

    df = pd.read_parquet(SILVER)
    df = df[df["seri_kode"].isin(SERI)]
    nasional = df[(df["wilayah_kode"].astype(str) == "9999") | (df["sumber"] != "bps")]

    tabel = (
        nasional.pivot_table(
            index="periode", columns="seri_kode", values="nilai", aggfunc="first"
        )
        .sort_index()
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tabel.to_csv(OUT)
    print(f"Tabel nasional: {OUT} ({tabel.shape[0]} periode x {tabel.shape[1]} seri)")
    print(f"periode_beririsan = {tabel.dropna().shape[0]}")


if __name__ == "__main__":
    main()