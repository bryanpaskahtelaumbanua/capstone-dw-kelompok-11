"""Kerangka tabel rekonsiliasi Tahap 6 (BPS vs WDI/ILO)."""

REKONSILIASI_COLS = [
    "pasangan", "seri_utama", "seri_pembanding", "periode",
    "nilai_seri_utama", "nilai_pembanding", "selisih",
    "kategori_penjelasan", "catatan",
]

PASANGAN = [
    {"id": "P1", "utama": "var543", "pembanding": "SL.UEM.TOTL.NE.ZS", "catatan": "estimasi nasional"},
    {"id": "P2", "utama": "var543", "pembanding": "SL.UEM.TOTL.ZS",    "catatan": "estimasi model ILO"},
    {"id": "P3", "utama": "var543", "pembanding": "SDG_0852_SEX_AGE_RT", "catatan": "rincian total; periksa bulan survei ILO"},
    {"id": "P4", "utama": None,     "pembanding": "SDG_0852_SEX_DSB_RT", "catatan": "konteks disabilitas; tanpa padanan BPS"},
]