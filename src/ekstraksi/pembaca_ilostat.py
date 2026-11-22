"""Tahap 1 — Pembaca ILOSTAT (SDMX-CSV, DSD JSON, metadata JSON).
Seri: SDG_0852_SEX_AGE_RT, SDG_0852_SEX_DSB_RT, UNE_DEAP_SEX_AGE_RT.

Tidak membersihkan apa pun. CSV: semua kolom SDMX dipertahankan teks aslinya
(TIME_PERIOD, OBS_VALUE, OBS_STATUS, NOTE_INDICATOR, FREQ, UNIT_MULT tidak diubah).
Hanya ditambah `periode` (triwulanan -> 2020-Q3) dan `jenis_periode`.
JSON: diratakan menjadi tabel panjang (json_path, nilai); kamus kode dari simpul id+nama.
Semua tabel membawa `_berkas_raw` dan `_sha256_raw` dari src.common.manifest.

Jumlah baris per berkas (isi dari `python -m src.ekstraksi.pembaca_ilostat --manifest`):
    # <path berkas> -> <jumlah baris>
"""
import csv
import json
import re
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.manifest import RAW, baca, sha256_raw  # noqa: E402

DATA_RAW = RAW  # dapat diganti saat pengujian
_WAJIB = ("REF_AREA", "TIME_PERIOD", "OBS_VALUE")
_POLA_Q = re.compile(r"^(\d{4})\s*[-_ ]?\s*Q([1-4])$", re.IGNORECASE)
_POLA_TAHUN = re.compile(r"^\d{4}$")


def _rel(p) -> str:
    return str(p).replace("\\", "/")


def _tempel(df: pd.DataFrame, rel: str) -> pd.DataFrame:
    df = df.copy()
    df["_berkas_raw"] = rel
    df["_sha256_raw"] = sha256_raw(rel)
    return df


def _bentuk_periode(t):
    """Kembalikan (periode, jenis_periode). Triwulanan -> 2020-Q3. Lainnya apa adanya."""
    if t is None or (isinstance(t, float) and pd.isna(t)):
        return None, None
    t = str(t).strip()
    m = _POLA_Q.match(t)
    if m:
        return f"{m.group(1)}-Q{m.group(2)}", "Triwulanan"
    if _POLA_TAHUN.match(t):
        return t, "Tahunan"
    return t, None


# ---------------------------------------------------------------- manifest
def berkas_ilostat(manifest: dict, ekstensi: str, bagian: str | None = None) -> list[str]:
    hasil = []
    for k in manifest:
        if not isinstance(k, str):
            continue
        r = _rel(k)
        if r.startswith("ilostat/") and r.lower().endswith(ekstensi):
            if bagian is None or f"/{bagian}/" in r:
                hasil.append(r)
    return sorted(hasil)


# ---------------------------------------------------------------- CSV
def baca_ilostat_csv(path_rel: str) -> pd.DataFrame:
    rel = _rel(path_rel)
    df = pd.read_csv(Path(DATA_RAW) / rel, dtype=str, keep_default_na=False,
                     na_values=[""], encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    hilang = [k for k in _WAJIB if k not in df.columns]
    if hilang:
        raise ValueError(f"{rel}: kolom wajib hilang {hilang}; kolom ada: {list(df.columns)}")

    pasangan = df["TIME_PERIOD"].map(_bentuk_periode)
    df["periode"] = pasangan.map(lambda x: x[0])
    df["jenis_periode"] = pasangan.map(lambda x: x[1])

    # FREQ=Q yang tak berbentuk triwulan = galat eksplisit, bukan hilang diam-diam
    if "FREQ" in df.columns:
        q = df["FREQ"].astype(str).str.upper().eq("Q")
        salah = q & (df["jenis_periode"] != "Triwulanan")
        if salah.any():
            raise ValueError(f"{rel}: {int(salah.sum())} baris FREQ=Q dengan TIME_PERIOD tak dikenal, "
                             f"contoh: {df.loc[salah, 'TIME_PERIOD'].iloc[0]!r}")
    return _tempel(df, rel)


def baca_ilostat_lengkap() -> pd.DataFrame:
    """Semua CSV data ILOSTAT di manifest (dipanggil src/ekstraksi/__init__.py)."""
    berkas = berkas_ilostat(baca(DATA_RAW), ".csv", "data")
    if not berkas:
        raise FileNotFoundError("Tidak ada berkas data ILOSTAT (.csv) di manifest")
    return pd.concat([baca_ilostat_csv(b) for b in berkas], ignore_index=True)


# ---------------------------------------------------------------- JSON
def _muat_json(rel: str):
    return json.loads((Path(DATA_RAW) / rel).read_text(encoding="utf-8-sig"))


def _daun(x, jalur="$"):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _daun(v, f"{jalur}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _daun(v, f"{jalur}[{i}]")
    else:
        yield jalur, x


def baca_ilostat_json(path_rel: str) -> pd.DataFrame:
    """Tabel panjang satu baris per daun JSON: json_path, nilai (teks asli)."""
    rel = _rel(path_rel)
    baris = [{"json_path": j, "nilai": None if v is None else str(v)}
             for j, v in _daun(_muat_json(rel))]
    if not baris:
        raise ValueError(f"{rel}: JSON tidak berisi nilai")
    return _tempel(pd.DataFrame(baris), rel)


def _nama(d: dict):
    n = d.get("name") or d.get("names") or d.get("label") or d.get("title")
    if isinstance(n, dict):
        n = n.get("en") or next(iter(n.values()), None)
    return n


def kamus_kode(path_rel: str) -> pd.DataFrame:
    """Simpul mana pun yang punya `id` dan nama: pemetaan kode -> label (SEX, AGE, dst.)."""
    rel = _rel(path_rel)
    hasil = []

    def jelajah(x, jalur):
        if isinstance(x, dict):
            if "id" in x and _nama(x) is not None:
                hasil.append({"induk": jalur, "kode": str(x["id"]), "nama": str(_nama(x))})
            for k, v in x.items():
                jelajah(v, f"{jalur}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                jelajah(v, f"{jalur}[{i}]")

    jelajah(_muat_json(rel), "$")
    df = pd.DataFrame(hasil, columns=["induk", "kode", "nama"])
    return _tempel(df, rel)


def baca_ilostat_json_semua() -> pd.DataFrame:
    berkas = berkas_ilostat(baca(DATA_RAW), ".json")
    if not berkas:
        raise FileNotFoundError("Tidak ada berkas JSON ILOSTAT di manifest")
    return pd.concat([baca_ilostat_json(b) for b in berkas], ignore_index=True)

def struktur_dsd(path_rel: str) -> pd.DataFrame:
    """Komponen DSD (dimensi, dimensi waktu, atribut, ukuran) beserta rujukan daftar kodenya."""
    rel = _rel(path_rel)
    daftar = (_muat_json(rel).get("data") or {}).get("dataStructures") or []
    if not daftar:
        raise ValueError(f"{rel}: tidak ada data.dataStructures")
    peta = (("dimension", "dimensionList", "dimensions"),
            ("time_dimension", "dimensionList", "timeDimensions"),
            ("attribute", "attributeList", "attributes"),
            ("measure", "measureList", "measures"))
    baris = []
    for ds in daftar:
        kom = ds.get("dataStructureComponents") or {}
        for bagian, blok, kunci in peta:
            for i, c in enumerate((kom.get(blok) or {}).get(kunci) or []):
                baris.append({
                    "struktur_id": ds.get("id"),
                    "bagian": bagian,
                    "posisi": c.get("position", i),
                    "komponen_id": c.get("id"),
                    "konsep": c.get("conceptIdentity"),
                    "daftar_kode": (c.get("localRepresentation") or {}).get("enumeration"),
                })
    if not baris:
        raise ValueError(f"{rel}: komponen DSD tidak ditemukan; kunci: {list(kom)}")
    return _tempel(pd.DataFrame(baris), rel)

# ---------------------------------------------------------------- uji
def uji_sintetis():
    global DATA_RAW, sha256_raw
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp)
        (raw / "ilostat/s/data").mkdir(parents=True)
        (raw / "ilostat/s/dsd").mkdir(parents=True)
        rel = "ilostat/s/data/DF_UNE_DEAP_SEX_AGE_RT.csv"
        (raw / rel).write_text(
            "DATAFLOW,REF_AREA,FREQ,TIME_PERIOD,OBS_VALUE,OBS_STATUS\n"
            "ILO:X,IDN,A,2020,4.25,\n"
            "ILO:X,IDN,Q,2020-Q3,4.50,\n"
            "ILO:X,IDN,Q,2020Q4,,B\n"
            "ILO:X,IDN,Q,2021-q1,4.10,\n", encoding="utf-8")
        relj = "ilostat/s/dsd/X.json"
        (raw / relj).write_text(json.dumps({"data": {"dimensions": [
            {"id": "SEX", "names": {"en": "Sex"}, "values": [{"id": "SEX_F", "name": "Female"}]}]}}),
            encoding="utf-8")
        asli = (DATA_RAW, sha256_raw)
        try:
            DATA_RAW, sha256_raw = raw, (lambda r: f"dummy_{r}")
            d = baca_ilostat_csv(rel)
            assert len(d) == 4                                           # tak ada baris hilang
            assert d["periode"].tolist() == ["2020", "2020-Q3", "2020-Q4", "2021-Q1"]
            assert d["jenis_periode"].tolist() == ["Tahunan"] + ["Triwulanan"] * 3
            assert d["TIME_PERIOD"].tolist()[2] == "2020Q4"              # kolom asal tidak diubah
            assert d["OBS_VALUE"].isna().sum() == 1 and d["OBS_STATUS"].iloc[2] == "B"
            assert d["_sha256_raw"].notna().all()
            j = baca_ilostat_json(relj)
            assert j["_berkas_raw"].eq(relj).all() and len(j) >= 4
            k = kamus_kode(relj)
            assert {"SEX", "SEX_F"} <= set(k["kode"])
            (raw / "ilostat/s/data/rusak.csv").write_text(
                "DATAFLOW,REF_AREA,FREQ,TIME_PERIOD,OBS_VALUE\nX,IDN,Q,2020-Triwulan3,1\n",
                encoding="utf-8")
            try:
                baca_ilostat_csv("ilostat/s/data/rusak.csv")
                raise AssertionError("seharusnya galat")
            except ValueError:
                pass
            print("[OK] Triwulanan (2020-Q3, 2020Q4, 2021-q1) terbaca sebagai 2020-Q3 dst.; "
                  "baris utuh; FREQ=Q tak dikenal menghentikan proses; JSON terbaca.")
        finally:
            DATA_RAW, sha256_raw = asli


def _hitung_baris_csv_mentah(rel: str) -> int:
    with open(Path(DATA_RAW) / rel, encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def uji_manifest_asli():
    manifest = baca(DATA_RAW)
    csvs = berkas_ilostat(manifest, ".csv", "data")
    jsons = berkas_ilostat(manifest, ".json")
    assert csvs and jsons, "CSV atau JSON ILOSTAT tidak ada di manifest"
    print("== CSV ==")
    for b in csvs:
        d = baca_ilostat_csv(b)
        n_mentah = _hitung_baris_csv_mentah(b)
        assert len(d) == n_mentah, f"{b}: terbaca {len(d)} != mentah {n_mentah}"
        assert (d["_berkas_raw"] == b).all() and d["_sha256_raw"].notna().all()
        assert (d["_sha256_raw"] == manifest[b]).all(), f"hash tak cocok: {b}"
        print(f"# {b} -> {len(d)} baris (hitungan mentah independen: {n_mentah})")
        if "DATAFLOW" in d.columns:
            print("    DATAFLOW:", sorted(d["DATAFLOW"].dropna().unique()))
        if "FREQ" in d.columns:
            print("    per FREQ:", d["FREQ"].value_counts(dropna=False).to_dict())
        print("    per jenis_periode:", d["jenis_periode"].value_counts(dropna=False).to_dict())
        tak_dikenal = d["periode"][d["jenis_periode"].isna()]
        print("    periode tak dikenal:", len(tak_dikenal), sorted(tak_dikenal.dropna().unique())[:5])
        q = d[d["jenis_periode"] == "Triwulanan"]
        if "FREQ" in d.columns:
            assert (d["FREQ"].astype(str).str.upper().eq("Q") == d["jenis_periode"].eq("Triwulanan")).all(), \
                f"{b}: FREQ=Q dan jenis_periode Triwulanan tidak sepadan"
        assert q["periode"].str.fullmatch(r"\d{4}-Q[1-4]").all()
        if len(q):
            print("    triwulan terbaca:", sorted(q['periode'].str[-2:].unique()),
                  "| rentang:", q["periode"].min(), "-", q["periode"].max())
        print("    kolom:", list(d.columns))
    print("== JSON ==")
    for b in jsons:
        j = baca_ilostat_json(b)
        k = kamus_kode(b)
        assert (j["_sha256_raw"] == manifest[b]).all(), f"hash tak cocok: {b}"
        print(f"# {b} -> {len(j)} baris (daun JSON) | simpul kode+nama: {len(k)}")

    print("== DSD vs kolom CSV ==")
    for b in berkas_ilostat(manifest, ".json", "dsd"):
        s = struktur_dsd(b)
        assert (s["_sha256_raw"] == manifest[b]).all(), f"hash tak cocok: {b}"
        csv_rel = "ilostat/" + b.split("/")[1] + "/data/DF_" + b.split("/")[-1].replace(".json", ".csv")
        assert csv_rel in csvs, f"{b}: CSV pasangannya {csv_rel} tidak ada di manifest"
        kol = set(baca_ilostat_csv(csv_rel).columns)
        selisih = set(s["komponen_id"]) - kol
        assert not selisih, f"{b}: komponen DSD tanpa kolom CSV: {sorted(selisih)}"
        print(f"# {b} -> {len(s)} komponen DSD, semuanya ada di kolom CSV")

    print(f"[OK] {len(csvs)} CSV dan {len(jsons)} JSON ILOSTAT terbaca; lineage cocok dengan MANIFEST.")

# ilostat/2026-10-20/data/DF_SDG_0852_SEX_AGE_RT.csv -> 216 baris
# ilostat/2026-10-20/data/DF_SDG_0852_SEX_DSB_RT.csv -> 81 baris
# ilostat/2026-10-20/data/DF_UNE_DEAP_SEX_AGE_RT.csv -> 5424 baris
# ilostat/2026-10-20/dsd/SDG_0852_SEX_AGE_RT.json -> 111 baris (daun JSON), 17 komponen DSD
# ilostat/2026-10-20/dsd/SDG_0852_SEX_DSB_RT.json -> 111 baris (daun JSON), 17 komponen DSD
# ilostat/2026-10-20/dsd/UNE_DEAP_SEX_AGE_RT.json -> 111 baris (daun JSON), 17 komponen DSD
# ilostat/2026-10-20/metadata/dataflow.json -> 26669 baris (daun JSON)

if __name__ == "__main__":
    if "--manifest" in sys.argv:
        uji_manifest_asli()
    else:
        uji_sintetis()