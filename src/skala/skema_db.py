"""Skema penyimpanan Silver & Gold (Tahap 5)."""
from pathlib import Path

DB_DIR = Path("data/db")
DB_DIR.mkdir(parents=True, exist_ok=True)
GOLD_DB = DB_DIR / "gold.duckdb"

SILVER_PK = ["sumber", "seri_kode", "wilayah_kode", "periode", "rincian", "_berkas_raw"]
GOLD_PK = ["wilayah_kode", "periode", "indikator"]

DDL_SILVER_SQLITE = """
CREATE TABLE IF NOT EXISTS silver (
    sumber TEXT, seri_kode TEXT, wilayah_kode TEXT, nama_wilayah TEXT,
    periode TEXT, jenis_periode TEXT, rincian TEXT, nilai REAL, satuan TEXT,
    _berkas_raw TEXT, _sha256_raw TEXT,
    PRIMARY KEY (sumber, seri_kode, wilayah_kode, periode, rincian, _berkas_raw)
);
"""

DDL_GOLD_DUCKDB = """
CREATE TABLE IF NOT EXISTS gold (
    wilayah_kode TEXT, nama_wilayah TEXT, periode TEXT, jenis_periode TEXT,
    indikator TEXT, nilai REAL,
    PRIMARY KEY (wilayah_kode, periode, indikator)
);
"""