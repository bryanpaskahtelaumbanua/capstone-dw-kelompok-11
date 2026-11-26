"""Tahap 4-6 - Reshape, integrasi, dan penyimpanan ke Gold (pertemuan VII, IX, XI, XII).

Keluaran: data/gold/*.parquet (panel provinsi x periode x indikator siap analisis, plus tabel
nasional dan rekonsiliasi dengan pembanding nasional).
"""
from src.gold.panel import bangun_panel_gold, pilih_sel_gold
from src.gold.pilih import ATURAN, pilih_satu_nilai, simpan


from src.gold.nasional import bangun_tabel_nasional

def jalankan(silver):
    nasional = bangun_tabel_nasional(silver)
    # bagian Gold lain (panel lebar, SQL) tetap dikerjakan komponen masing-masing
    return {"nasional": nasional}
    """Terima Silver, tulis tabel Gold, kembalikan {nama_tabel: DataFrame}."""
    panel = bangun_panel_gold(silver)
    terpilih, tidak, ringkasan = pilih_satu_nilai(silver, ATURAN)
    simpan(terpilih, tidak, ringkasan)          # hitungan tak-terpilih per alasan untuk log
    return {"panel": panel}


__all__ = ["jalankan", "bangun_panel_gold", "pilih_sel_gold"]
