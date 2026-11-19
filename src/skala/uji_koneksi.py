"""Uji koneksi & skema penyimpanan lokal (tanpa data mentah)."""
import sqlite3
import duckdb
from src.skala.skema_db import DB_DIR, GOLD_DB, DDL_SILVER_SQLITE, DDL_GOLD_DUCKDB


def main():
    DB_DIR.mkdir(parents=True, exist_ok=True)

    sqlite_path = DB_DIR / "silver.sqlite"
    con = sqlite3.connect(sqlite_path)
    con.execute(DDL_SILVER_SQLITE)
    con.commit()
    con.close()
    print("SQLite OK:", sqlite_path)

    ddb = duckdb.connect(str(GOLD_DB))
    ddb.execute(DDL_GOLD_DUCKDB)
    ddb.close()
    print("DuckDB OK:", GOLD_DB)


if __name__ == "__main__":
    main()