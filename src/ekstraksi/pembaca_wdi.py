"""Tahap 1 — Pembaca WDI (JSON data dan metadata). Seri: SL.UEM.TOTL.ZS, SL.UEM.TOTL.NE.ZS.

Tidak membersihkan apa pun: hanya meratakan struktur, menyaring menurut indicator.id,
dan menempelkan `_berkas_raw` serta `_sha256_raw` dari src.common.manifest.

Jumlah baris per berkas (isi dari keluaran `python -m src.ekstraksi.pembaca_wdi --manifest`):
    # <path berkas> -> <baris tersaring> dari <rekaman dalam berkas>
"""
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.manifest import RAW, baca, sha256_raw  # noqa: E402

DATA_RAW = RAW  # dapat diganti saat pengujian
SERI = ("SL.UEM.TOTL.ZS", "SL.UEM.TOTL.NE.ZS")
_KOLOM_ASAL = ["_berkas_raw", "_sha256_raw"]


def berkas_wdi_dari_manifest(manifest: dict) -> list[str]:
    """Path relatif (terhadap data/raw) semua berkas .json WDI di manifest."""
    return sorted(k for k in manifest
                  if isinstance(k, str) and k.replace("\\", "/").startswith("wdi/")
                  and k.lower().endswith(".json"))


def _jenis(rel: str) -> str:
    return "data" if "/data/" in rel else "metadata"


def _muat(rel: str):
    teks = (Path(DATA_RAW) / rel).read_text(encoding="utf-8-sig")
    return json.loads(teks)


def _rekaman(payload, rel: str) -> list[dict]:
    """WDI: [meta_halaman, [rekaman, ...]]. Pesan galat API ikut dihentikan."""
    if isinstance(payload, list) and payload and isinstance(payload[0], dict) \
            and "message" in payload[0] and len(payload) == 1:
        raise ValueError(f"{rel}: respons galat WDI: {payload[0]['message']}")
    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list):
        return [r for r in payload[1] if isinstance(r, dict)]
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(f"{rel}: struktur JSON tak dikenali ({type(payload).__name__})")


def _id_indikator(rec: dict):
    ind = rec.get("indicator")
    if isinstance(ind, dict):          # berkas data
        return ind.get("id")
    return rec.get("id")               # berkas metadata


def _ratakan(d: dict, awal: str = "") -> dict:
    out = {}
    for k, v in d.items():
        kunci = f"{awal}{k}"
        if isinstance(v, dict):
            out.update(_ratakan(v, kunci + "_"))
        elif isinstance(v, list):
            out[kunci] = json.dumps(v, ensure_ascii=False)
        else:
            out[kunci] = v
    return out


def baca_wdi_berkas(rel: str) -> tuple[pd.DataFrame, int]:
    """Baca satu berkas WDI. Kembalikan (tabel tersaring, jumlah rekaman dalam berkas)."""
    rel = str(rel).replace("\\", "/")
    rekaman = _rekaman(_muat(rel), rel)
    cocok = [_ratakan(r) for r in rekaman if _id_indikator(r) in SERI]
    df = pd.DataFrame(cocok)
    if df.empty:
        df = pd.DataFrame(columns=_KOLOM_ASAL)
    else:
        df["_berkas_raw"] = rel
        df["_sha256_raw"] = sha256_raw(rel)
    return df, len(rekaman)


def _baca_jenis(jenis: str) -> pd.DataFrame:
    berkas = [b for b in berkas_wdi_dari_manifest(baca(DATA_RAW)) if _jenis(b) == jenis]
    if not berkas:
        raise FileNotFoundError(f"Tidak ada berkas WDI ({jenis}) di manifest")
    return pd.concat([baca_wdi_berkas(b)[0] for b in berkas], ignore_index=True)


def baca_wdi_json() -> pd.DataFrame:
    """Pengamatan WDI (berkas data/) untuk dua seri kasus, tabel panjang."""
    return _baca_jenis("data")


def baca_wdi_metadata() -> pd.DataFrame:
    """Rekaman metadata indikator (berkas metadata/) untuk dua seri kasus."""
    return _baca_jenis("metadata")


# ---------------------------------------------------------------- uji
def uji_sintetis():
    global DATA_RAW, sha256_raw
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp)
        (raw / "wdi" / "s" / "data").mkdir(parents=True)
        (raw / "wdi" / "s" / "metadata").mkdir(parents=True)
        obs = lambda i, thn, v: {"indicator": {"id": i, "value": "x"},  # noqa: E731
                                 "country": {"id": "ID", "value": "Indonesia"},
                                 "countryiso3code": "IDN", "date": thn, "value": v,
                                 "unit": "", "obs_status": "", "decimal": 1}
        data = [{"page": 1, "pages": 1, "total": 4},
                [obs("SL.UEM.TOTL.ZS", "2020", 4.25), obs("SL.UEM.TOTL.NE.ZS", "2020", 4.1),
                 obs("SL.UEM.TOTL.ZS", "2021", None), obs("NY.GDP.MKTP.CD", "2020", 9.9)]]
        meta = [{"page": 1}, [{"id": "SL.UEM.TOTL.ZS", "name": "Unemployment", "sourceNote": "n"},
                              {"id": "XX.OTHER", "name": "lain"}]]
        (raw / "wdi/s/data/a.json").write_text(json.dumps(data), encoding="utf-8")
        (raw / "wdi/s/metadata/i.json").write_text(json.dumps(meta), encoding="utf-8")
        asli = (DATA_RAW, sha256_raw)
        try:
            DATA_RAW, sha256_raw = raw, (lambda r: f"dummy_{r}")
            d, n = baca_wdi_berkas("wdi/s/data/a.json")
            assert n == 4 and len(d) == 3, (n, len(d))          # indikator lain tersaring
            assert d["value"].isna().sum() == 1                  # null tetap ada, tidak dibuang
            assert (d["_berkas_raw"] == "wdi/s/data/a.json").all()
            assert d["_sha256_raw"].notna().all()
            m, nm = baca_wdi_berkas("wdi/s/metadata/i.json")
            assert nm == 2 and len(m) == 1 and m["name"].iloc[0] == "Unemployment"
            print("[OK] Saringan indicator.id, null dipertahankan, lineage terpasang.")
        finally:
            DATA_RAW, sha256_raw = asli


def uji_manifest_asli():
    """Jalankan setelah `python unduh_data.py --kasus 11`: tabel per berkas + pemeriksaan lineage."""
    manifest = baca(DATA_RAW)
    berkas = berkas_wdi_dari_manifest(manifest)
    assert berkas, "Tidak ada berkas WDI di manifest"
    print(f"{'berkas':58} {'jenis':9} {'rekaman':>8} {'tersaring':>9}  lineage")
    for b in berkas:
        df, n = baca_wdi_berkas(b)
        ok = (
            (df["_berkas_raw"] == b).all()
            and df["_sha256_raw"].notna().all()
            and (df["_sha256_raw"] == manifest[b]).all()
        ) if len(df) else True
        assert ok, f"{b}: lineage tidak cocok dengan manifest"
        if _jenis(b) == "data":
            assert len(df) > 0, f"{b}: tidak ada baris untuk {SERI}"
        status = f"OK ({len(df)}/{len(df)} baris)" if len(df) else "tidak ada baris (tidak diuji)"
        print(f"{b:58} {_jenis(b):9} {n:>8} {len(df):>9}  {status}")
        print(f"# {b} -> {len(df)} baris tersaring dari {n} rekaman")
    print(f"[OK] {len(berkas)} berkas WDI dari manifest terbaca; lineage cocok dengan MANIFEST.")


if __name__ == "__main__":
    if "--manifest" in sys.argv:
        uji_manifest_asli()
    else:
        uji_sintetis()