"""Tahap 1 — Pembaca BPS (CSV dan JSON WebAPI). Seri: var543.

Tidak membersihkan apa pun: hanya meratakan struktur menjadi tabel panjang,
mempertahankan kolom asal, lalu menempelkan `_berkas_raw` dan `_sha256_raw`.

Jumlah baris per berkas (isi setelah menjalankan `python -m src.ekstraksi.pembaca_bps --hitung`):
    # <path berkas>  -> <jumlah baris>

Uji mandiri: `python -m src.ekstraksi.pembaca_bps`
"""
import csv
import hashlib
import io
import itertools
import json
import re
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.manifest import RAW, baca  # noqa: E402

DATA_RAW = RAW  # dapat diganti saat pengujian

# Peta label periode BPS -> jenis_periode. Label tak dikenal tidak dibuang,
# dibiarkan apa adanya.
PERIODE = {"februari": "Februari", "agustus": "Agustus", "tahunan": "Tahunan"}

_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def _rel(path_rel: str) -> str:
    return str(path_rel).replace("\\", "/")


def sha256_raw(path_rel: str) -> str:
    """sha256 berkas mentah: dari manifest bila ada, selain itu dihitung langsung."""
    rel = _rel(path_rel)
    try:
        for item in baca(DATA_RAW).get("files", []):
            if isinstance(item, dict) and (item.get("path") or item.get("berkas")) == rel:
                if item.get("sha256"):
                    return item["sha256"]
    except Exception:
        pass
    h = hashlib.sha256()
    with open(Path(DATA_RAW) / rel, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def _baca_teks(path: Path) -> str:
    mentah = path.read_bytes()
    for enc in _ENCODINGS:
        try:
            return mentah.decode(enc)
        except UnicodeDecodeError:
            continue
    return mentah.decode("latin-1", errors="replace")


def _tempel_asal(df: pd.DataFrame, rel: str) -> pd.DataFrame:
    df = df.copy()
    df["_berkas_raw"] = rel
    df["_sha256_raw"] = sha256_raw(rel)
    return df


def _petakan_periode(label) -> str | None:
    if label is None or (isinstance(label, float) and pd.isna(label)):
        return None
    return PERIODE.get(str(label).strip().lower(), str(label).strip())


def _desimal_koma(serie: pd.Series) -> bool:
    s = serie.dropna().astype(str)
    koma = s.str.fullmatch(r"-?\d+,\d+").sum()
    titik = s.str.fullmatch(r"-?\d+\.\d+").sum()
    return koma > 0 and titik == 0


# ---------------------------------------------------------------- CSV
def baca_bps_csv(path_rel: str) -> pd.DataFrame:
    rel = _rel(path_rel)
    teks = _baca_teks(Path(DATA_RAW) / rel)
    try:
        delim = csv.Sniffer().sniff(teks[:4096], delimiters=",;\t|").delimiter
    except csv.Error:
        delim = ";" if teks.count(";") > teks.count(",") else ","
    df = pd.read_csv(io.StringIO(teks), sep=delim, dtype=str,
                     keep_default_na=False, na_values=[""])
    df.columns = [c.strip() for c in df.columns]

    # periode: label periode BPS bisa bernama jenis_periode / turtahun / periode
    kol_periode = next((k for k in ("jenis_periode", "turtahun", "periode") if k in df.columns), None)
    if kol_periode is None:
        raise ValueError(f"{rel}: tidak ada kolom periode; kolom ada: {list(df.columns)}")
    df["jenis_periode"] = df[kol_periode].map(_petakan_periode)

    # nilai: simpan teks asli, tambahkan versi numerik sesuai pemisah desimal berkas
    if "nilai" in df.columns:
        df["nilai_raw"] = df["nilai"]
        s = df["nilai"]
        if _desimal_koma(s):
            s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df["nilai"] = pd.to_numeric(s, errors="coerce")
    return _tempel_asal(df, rel)


# ---------------------------------------------------------------- JSON
def _buka_halaman(payload) -> list[dict]:
    """Kembalikan daftar objek halaman. BPS kadang membungkus data dalam
    {'data': [meta, {...}]}, atau satu berkas berisi daftar halaman."""
    if isinstance(payload, list):
        # format ringkas: daftar rekaman datar
        if payload and all(isinstance(p, dict) and "datacontent" in p and "vervar" in p
                           and not isinstance(p["vervar"], list) for p in payload):
            return [{"_ringkas": payload}]
        halaman = []
        for p in payload:
            halaman.extend(_buka_halaman(p))
        return halaman
    if isinstance(payload, dict):
        if "datacontent" in payload:
            return [payload]
        if "data" in payload:
            return _buka_halaman(payload["data"])
    return []


def _daftar(obj, kunci):
    return [(str(x.get("val")), x.get("label")) for x in obj.get(kunci, []) or []]


def _ratakan_halaman(h: dict) -> list[dict]:
    var = _daftar(h, "var") or [("", None)]
    vervar = _daftar(h, "vervar") or [("", None)]
    turvar = _daftar(h, "turvar") or [("", None)]
    tahun = _daftar(h, "tahun") or [("", None)]
    turtahun = _daftar(h, "turtahun") or [("", None)]

    # kunci datacontent = vervar + var + turvar + tahun + turtahun (digabung)
    indeks = {}
    for v, vr, tv, th, tt in itertools.product(vervar, var, turvar, tahun, turtahun):
        indeks.setdefault(v[0] + vr[0] + tv[0] + th[0] + tt[0], (v, vr, tv, th, tt))

    baris = []
    for kunci, nilai in (h.get("datacontent") or {}).items():
        komb = indeks.get(str(kunci))
        if komb is None:
            raise ValueError(f"Kunci datacontent tak terurai: {kunci}")
        v, vr, tv, th, tt = komb
        baris.append({
            "vervar": v[0], "vervar_label": v[1],
            "var": vr[0], "var_label": vr[1],
            "turvar": tv[0], "turvar_label": tv[1],
            "tahun": th[0], "tahun_label": th[1],
            "turtahun": tt[0], "turtahun_label": tt[1],
            "jenis_periode": _petakan_periode(tt[1]),
            "nilai": nilai,
        })
    return baris


def _ratakan_ringkas(rekaman: list[dict]) -> list[dict]:
    baris = []
    for r in rekaman:
        for thn, nilai in (r.get("datacontent") or {}).items():
            baris.append({
                "vervar": r.get("vervar"), "turtahun_label": r.get("turtahun"),
                "tahun": thn, "jenis_periode": _petakan_periode(r.get("turtahun")),
                "nilai": nilai,
            })
    return baris


def baca_bps_json(path_rel: str) -> pd.DataFrame:
    rel = _rel(path_rel)
    payload = json.loads(_baca_teks(Path(DATA_RAW) / rel))
    baris = []
    for h in _buka_halaman(payload):
        baris.extend(_ratakan_ringkas(h["_ringkas"]) if "_ringkas" in h else _ratakan_halaman(h))
    df = pd.DataFrame(baris)
    if df.empty:
        raise ValueError(f"Tidak ada datacontent terbaca dari {rel}")
    return _tempel_asal(df, rel)


# ---------------------------------------------------------------- manifest
_POLA_BPS = re.compile(r"^(?:.*[/\\])?(bps[/\\].+\.(?:csv|json))$", re.IGNORECASE)


def ambil_berkas_bps_dari_manifest(data_manifest) -> list[str]:
    """Telusuri manifest apa pun bentuknya; kembalikan path relatif berkas BPS."""
    hasil = []

    def jelajah(x):
        if isinstance(x, dict):
            for k, v in x.items():
                jelajah(k)
                jelajah(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                jelajah(v)
        elif isinstance(x, str):
            m = _POLA_BPS.match(x.strip())
            if m and not m.group(1).lower().endswith("manifest_asal.json"):
                hasil.append(m.group(1).replace("\\", "/"))

    jelajah(data_manifest)
    return list(dict.fromkeys(hasil))

def berkas_bps_metadata(data_manifest) -> list[str]:
    """Berkas manifest_asal.json BPS di manifest (catatan unduhan, bukan data)."""
    return sorted(
        str(k).replace("\\", "/") for k in data_manifest
        if isinstance(k, str) and str(k).replace("\\", "/").lower().startswith("bps/")
        and str(k).lower().endswith("manifest_asal.json")
    )


def _daun_json(x, jalur="$"):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _daun_json(v, f"{jalur}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _daun_json(v, f"{jalur}[{i}]")
    else:
        yield jalur, x


def baca_bps_metadata(path_rel: str) -> pd.DataFrame:
    """Tabel panjang (json_path, nilai) dari catatan unduhan BPS; tidak ada yang disaring."""
    rel = _rel(path_rel)
    payload = json.loads(_baca_teks(Path(DATA_RAW) / rel))
    baris = [{"json_path": j, "nilai": None if v is None else str(v)}
             for j, v in _daun_json(payload)]
    if not baris:
        raise ValueError(f"{rel}: JSON tidak berisi nilai")
    return _tempel_asal(pd.DataFrame(baris), rel)
    
# ---------------------------------------------------------------- uji mandiri
def uji_periode_dan_manifest():
    global DATA_RAW, sha256_raw
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_dir = Path(tmp_dir) / "data" / "raw"
        (raw_dir / "bps" / "2026-10-17" / "json").mkdir(parents=True, exist_ok=True)

        rel_csv = "bps/2026-10-17/sdg8_tpt.csv"
        rel_json = "bps/2026-10-17/json/sdg8_tpt.json"

        (raw_dir / rel_csv).write_text(
            "vervar,tahun,jenis_periode,nilai\n"
            "1800,2025,Februari,4.12\n"
            "1800,2025,Agustus,4.35\n"
            "1800,2025,Tahunan,4.24\n",
            encoding="utf-8",
        )
        payload_json = [
            {"vervar": "1800", "turtahun": "Februari", "datacontent": {"2025": 4.12}},
            {"vervar": "1800", "turtahun": "Agustus", "datacontent": {"2025": 4.35}},
            {"vervar": "1800", "turtahun": "Tahunan", "datacontent": {"2025": 4.24}},
        ]
        (raw_dir / rel_json).write_text(json.dumps(payload_json), encoding="utf-8")

        manifest_dummy = {"files": [
            {"path": rel_csv, "source": "bps"},
            {"path": rel_json, "source": "bps"},
            {"path": "non_bps/2026-10-17/lain.csv", "source": "lain"},
        ]}

        raw_asli, sha_asli = DATA_RAW, sha256_raw
        try:
            DATA_RAW = raw_dir
            sha256_raw = lambda rel: f"dummy_sha256_{rel}"  # noqa: E731

            df_csv = baca_bps_csv(rel_csv)
            df_json = baca_bps_json(rel_json)

            diharapkan = {"Februari", "Agustus", "Tahunan"}
            assert diharapkan <= set(df_csv["jenis_periode"].dropna()), "CSV kurang periode"
            assert diharapkan <= set(df_json["jenis_periode"].dropna()), "JSON kurang periode"
            print("[OK] Pemetaan Februari, Agustus, dan Tahunan valid pada CSV & JSON.")

            berkas = ambil_berkas_bps_dari_manifest(manifest_dummy)
            assert len(berkas) == 2
            semua = pd.concat(
                [baca_bps_csv(b) if b.endswith(".csv") else baca_bps_json(b) for b in berkas],
                ignore_index=True,
            )
            assert set(semua["_berkas_raw"]) == set(berkas)
            assert semua["_sha256_raw"].notna().all()
            print(f"[OK] Seluruh {len(berkas)} berkas BPS dalam manifest berhasil diproses.")
        finally:
            DATA_RAW, sha256_raw = raw_asli, sha_asli


def hitung_baris_semua():
    """Cetak jumlah baris per berkas BPS di data/raw/ untuk disalin ke docstring."""
    for p in sorted((Path(DATA_RAW) / "bps").glob("**/*")):
        rel = str(p.relative_to(DATA_RAW)).replace("\\", "/")
        if p.suffix == ".csv":
            df = baca_bps_csv(rel)
        elif p.suffix == ".json" and p.name != "manifest_asal.json":
            df = baca_bps_json(rel)
        else:
            continue
        assert df["_sha256_raw"].notna().all()
        print(f"# {rel} -> {len(df)} baris | periode: {sorted(df['jenis_periode'].dropna().unique())}")

def uji_json_bersarang_dan_nilai():
    """Struktur BPS asli (halaman bersarang) + nilai harus jatuh pada periode yang benar."""
    global DATA_RAW, sha256_raw
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_dir = Path(tmp_dir)
        (raw_dir / "bps").mkdir()
        tp = [{"val": 1, "label": "Februari"}, {"val": 2, "label": "Agustus"},
              {"val": 3, "label": "Tahunan"}]
        nilai = {1: 4.12, 2: 4.35, 3: 4.24}

        def halaman(thn_val, thn_label):
            return {
                "vervar": [{"val": 1800, "label": "Lampung"}],
                "var": [{"val": 543, "label": "TPT"}],
                "turvar": [{"val": 0, "label": "Tidak ada"}],
                "tahun": [{"val": thn_val, "label": thn_label}],
                "turtahun": tp,
                "datacontent": {f"18005430{thn_val}{t['val']}": nilai[t["val"]] for t in tp},
            }

        # dua halaman tahun dalam satu berkas, dibungkus gaya BPS
        payload = {"status": "OK", "data": [{"page": 1}, halaman(125, "2025"), halaman(124, "2024")]}
        rel = "bps/nested.json"
        (raw_dir / rel).write_text(json.dumps(payload), encoding="utf-8")

        # CSV tanpa jenis_periode: harus dipetakan dari turtahun, desimal koma
        rel_csv = "bps/koma.csv"
        (raw_dir / rel_csv).write_text(
            "vervar;tahun;turtahun;nilai\n1800;2025;Februari;4,12\n"
            "1800;2025;Agustus;4,35\n1800;2025;Tahunan;4,24\n", encoding="cp1252")

        raw_asli, sha_asli = DATA_RAW, sha256_raw
        try:
            DATA_RAW = raw_dir
            sha256_raw = lambda r: f"dummy_{r}"  # noqa: E731
            df = baca_bps_json(rel)
            assert len(df) == 6, len(df)                     # 2 tahun x 3 periode
            assert set(df["tahun"]) == {"125", "124"}
            for periode, v in [("Februari", 4.12), ("Agustus", 4.35), ("Tahunan", 4.24)]:
                sub = df[df["jenis_periode"] == periode]
                assert len(sub) == 2 and (sub["nilai"] == v).all(), (periode, sub)

            dc = baca_bps_csv(rel_csv)
            assert dict(zip(dc["jenis_periode"], dc["nilai"])) == \
                {"Februari": 4.12, "Agustus": 4.35, "Tahunan": 4.24}
            print("[OK] JSON bersarang + CSV desimal-koma: nilai jatuh pada periode yang benar.")
        finally:
            DATA_RAW, sha256_raw = raw_asli, sha_asli


def uji_manifest_asli():
    """Jalankan setelah `python unduh_data.py --kasus 11`. Memakai manifest dan hash asli."""
    manifest = baca(DATA_RAW)
    berkas = ambil_berkas_bps_dari_manifest(manifest)
    assert berkas, "Tidak ada berkas BPS di manifest"
    hash_manifest = {(i.get("path") or i.get("berkas")): i.get("sha256")
                     for i in manifest.get("files", []) if isinstance(i, dict)}
    terproses = set()
    for b in berkas:
        if b.endswith(".csv"):
            df = baca_bps_csv(b)
        elif b.endswith(".json"):
            df = baca_bps_json(b)
        else:
            continue
        assert len(df) > 0, f"{b} kosong"
        assert (df["_berkas_raw"] == b).all()
        assert df["_sha256_raw"].notna().all()
        if hash_manifest.get(b):
            assert (df["_sha256_raw"] == hash_manifest[b]).all(), f"hash tak cocok: {b}"
        terproses.add(b)
        print(f"# {b} -> {len(df)} baris | periode: {sorted(df['jenis_periode'].dropna().unique())}")
    assert terproses == {b for b in berkas if b.endswith((".csv", ".json"))}
    print(f"[OK] {len(terproses)} berkas BPS dari manifest asli terbaca.")

if __name__ == "__main__":
    if "--hitung" in sys.argv:
        hitung_baris_semua()
    elif "--manifest" in sys.argv:
        uji_manifest_asli()
    else:
        uji_periode_dan_manifest()
        uji_json_bersarang_dan_nilai()