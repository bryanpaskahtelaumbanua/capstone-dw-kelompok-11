"""Skrip pemuat Silver (Parquet) ke SQLite & Gold ke DuckDB."""
import sqlite3
import duckdb
import pandas as pd
from pathlib import Path
from src.skala.skema_db import DB_DIR, GOLD_DB, DDL_SILVER_SQLITE, DDL_GOLD_DUCKDB

SILVER = Path("data/silver/silver.parquet")
SQLITE_PATH = DB_DIR / "silver.sqlite"

def main():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Muat Silver ke SQLite
    if SILVER.exists():
        df_silver = pd.read_parquet(SILVER)
        con = sqlite3.connect(SQLITE_PATH)
        con.execute(DDL_SILVER_SQLITE)
        # Ganti tabel jika sudah ada agar bersih setiap kali dijalankan
        con.execute("DELETE FROM silver") 
        df_silver.to_sql("silver", con, if_exists="append", index=False)
        con.commit()
        con.close()
        print(f"Sukses memuat {len(df_silver)} baris Silver ke {SQLITE_PATH}")
    else:
        print(f"Silver belum ada di {SILVER}. Menunggu komponen Transformasi.")

    # 2. Siapkan Gold di DuckDB (Kosongkan jika sudah ada)
    ddb = duckdb.connect(str(GOLD_DB))
    ddb.execute(DDL_GOLD_DUCKDB)
    ddb.close()
    print(f"Skema Gold siap di {GOLD_DB}")

if __name__ == "__main__":
    main()