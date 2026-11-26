"""Tahap 4–6 — Reshape, integrasi, dan penyimpanan ke Gold (pertemuan VII, IX, XI, XII). Milik tim.

Keluaran: data/gold/*.parquet (panel provinsi x tahun x indikator siap analisis, plus tabel
rekonsiliasi dengan pembanding nasional) dan basis data SQL (mis. data/gold/gold.sqlite).
"""


from src.gold.nasional import bangun_tabel_nasional

def jalankan(silver):
    nasional = bangun_tabel_nasional(silver)
    # bagian Gold lain (panel lebar, SQL) tetap dikerjakan komponen masing-masing
    return {"nasional": nasional}
