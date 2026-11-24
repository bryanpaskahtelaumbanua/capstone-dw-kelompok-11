"""Tahap 4-6 - Reshape, integrasi, dan penyimpanan ke Gold (pertemuan VII, IX, XI, XII).

Keluaran: data/gold/*.parquet (panel provinsi x periode x indikator siap analisis, plus tabel
nasional dan rekonsiliasi dengan pembanding nasional).
"""
from src.gold.panel import bangun_panel_gold, pilih_sel_gold


def jalankan(silver):
    """Terima Silver, tulis tabel Gold, kembalikan {nama_tabel: DataFrame}."""
    panel = bangun_panel_gold(silver)
    return {"panel": panel}


__all__ = ["jalankan", "bangun_panel_gold", "pilih_sel_gold"]
