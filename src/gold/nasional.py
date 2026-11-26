"""Tahap 6 (persiapan) — Tabel nasional Gold: satu baris per seri x periode.

Seri utama : var543 (BPS, tingkat pengangguran terbuka).
Pembanding : SDG_0852_SEX_AGE_RT, SDG_0852_SEX_DSB_RT, UNE_DEAP_SEX_AGE_RT (ILO),
             SL.UEM.TOTL.ZS, SL.UEM.TOTL.NE.ZS (WDI).

Kolom `asal_nilai` menyatakan asal setiap angka nasional:
  baris_indonesia  : baris Indonesia (wilayah_kode 9999) yang diterbitkan seri utama
  agregat_provinsi : tidak dipakai (lihat aturan di bawah)
  pembanding       : angka nasional seri pembanding (ILO atau WDI, hanya Indonesia)

Aturan agregat provinsi (TIDAK dipakai, karena var543 menerbitkan baris Indonesia):
  TPT adalah rasio pengangguran terhadap angkatan kerja, jadi agregat nasional yang benar
  adalah rata-rata TPT provinsi berbobot ANGKATAN KERJA provinsi. Angkatan kerja tidak ada
  di paket (perlu data pendukung, panduan bagian 1.1); rata-rata sederhana atau berbobot
  penduduk bias. Bila baris Indonesia tidak ada pada suatu periode, periode itu dinyatakan
  tanpa padanan nasional dan tidak diisi.

Rincian: hanya `total` (RINCIAN_TOTAL menimpa per seri bila Silver memakai nama lain).

Jalankan: `python -m src.gold.nasional` (uji sintetis) atau `--cek` (Silver asli, tanpa menulis).
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.manifest import RAW, baca  # noqa: E402

SILVER = ROOT / "data" / "silver" / "silver.parquet"
GOLD = ROOT / "data" / "gold"
KELUARAN = GOLD / "tabel_nasional.parquet"

UTAMA = "var543"
PEMBANDING_ILO = ("SDG_0852_SEX_AGE_RT", "SDG_0852_SEX_DSB_RT", "UNE_DEAP_SEX_AGE_RT")
PEMBANDING_WDI = ("SL.UEM.TOTL.ZS", "SL.UEM.TOTL.NE.ZS")
TOTAL = "total"
# Rincian keseluruhan per seri. Seri tanpa entri memakai "total" (var543, WDI).
# Rincian ILO di Silver berupa kode mentah "SEX|AGE"; keseluruhan = semua jenis kelamin dan
# kelompok umur 15+ (cakupan sama dengan TPT BPS). Nama DSB terkonfirmasi dari Silver;
# dua nama AGE_YTHADULT_YGE15 adalah dugaan dan HARUS dicek dengan perintah profil rincian.
RINCIAN_TOTAL: dict = {
    "SDG_0852_SEX_DSB_RT": "SEX_T|DSB_STATUS_TOTAL",
    "SDG_0852_SEX_AGE_RT": "SEX_T|AGE_YTHADULT_YGE15",
    "UNE_DEAP_SEX_AGE_RT": "SEX_T|AGE_YTHADULT_YGE15",
}
KOLOM = ["seri_kode", "periode", "jenis_periode", "rincian", "wilayah_kode", "nilai_nasional",
         "satuan", "sumber", "asal_nilai", "_berkas_raw", "_sha256_raw"]
WAJIB_SILVER = {"sumber", "seri_kode", "wilayah_kode", "periode", "jenis_periode", "rincian",
                "nilai", "satuan", "_berkas_raw", "_sha256_raw"}


def _muat_silver(silver) -> pd.DataFrame:
    s = silver if isinstance(silver, pd.DataFrame) else pd.read_parquet(SILVER)
    kurang = WAJIB_SILVER - set(s.columns)
    if kurang:
        raise ValueError(f"Silver kekurangan kolom: {sorted(kurang)}")
    return s


def _kode_nasional(s: pd.DataFrame):
    return 9999 if pd.api.types.is_integer_dtype(s["wilayah_kode"]) else "9999"


def _rincian_total(d: pd.DataFrame, seri: str) -> pd.DataFrame:
    nama = RINCIAN_TOTAL.get(seri, TOTAL)
    t = d[d["rincian"].astype(str) == nama]
    if t.empty:
        kandidat = sorted(x for x in d["rincian"].astype(str).unique()
                          if "total" in x.lower() or x.upper().startswith("SEX_T"))[:40]
        raise ValueError(f"{seri}: rincian '{nama}' tidak ada ({d['rincian'].nunique()} rincian). "
                         f"Kandidat: {kandidat}. Isi RINCIAN_TOTAL untuk seri ini.")
    return t


def _dari_silver(d: pd.DataFrame, asal: str, kode_nas) -> pd.DataFrame:
    return pd.DataFrame({
        "seri_kode": d["seri_kode"].values,
        "periode": d["periode"].astype(str).values,
        "jenis_periode": d["jenis_periode"].values,
        "rincian": d["rincian"].values,
        "wilayah_kode": kode_nas,
        "nilai_nasional": pd.to_numeric(d["nilai"]).values,
        "satuan": d["satuan"].values,
        "sumber": d["sumber"].values,
        "asal_nilai": asal,
        "_berkas_raw": d["_berkas_raw"].values,
        "_sha256_raw": d["_sha256_raw"].values,
    })


def _utama(s: pd.DataFrame, kode_nas) -> pd.DataFrame:
    d = s[s["seri_kode"] == UTAMA]
    if d.empty:
        raise ValueError(f"{UTAMA} tidak ada di Silver; seri_kode tersedia: {sorted(s['seri_kode'].unique())}")
    nas = d[d["wilayah_kode"].astype(str) == str(kode_nas)]
    if nas.empty:
        raise ValueError(f"{UTAMA}: tidak ada baris Indonesia ({kode_nas}). Putuskan aturan agregat atau "
                         f"nyatakan tanpa padanan nasional (lihat docstring) dan catat di log.")
    nas = _rincian_total(nas, UTAMA)
    prov = d[(d["wilayah_kode"].astype(str) != str(kode_nas))
             & (d["rincian"].astype(str) == RINCIAN_TOTAL.get(UTAMA, TOTAL))]
    tanpa = sorted(set(prov["periode"].astype(str)) - set(nas["periode"].astype(str)))
    print(f"    {UTAMA}: {len(nas)} periode punya baris Indonesia; "
          f"{len(tanpa)} periode provinsi tanpa baris Indonesia (tidak diagregasi)")
    if tanpa:
        print("      tanpa padanan nasional:", tanpa[:10])
    return _dari_silver(nas, "baris_indonesia", kode_nas)


def _pembanding_silver(s: pd.DataFrame, seri: str, kode_nas) -> pd.DataFrame:
    d = s[s["seri_kode"] == seri]
    if d.empty:
        raise ValueError(f"{seri} tidak ada di Silver; seri_kode tersedia: {sorted(s['seri_kode'].unique())}")
    if d["wilayah_kode"].nunique() != 1:
        raise ValueError(f"{seri}: pembanding nasional harus satu wilayah, ada {d['wilayah_kode'].nunique()}")
    return _dari_silver(_rincian_total(d, seri), "pembanding", kode_nas)


def _label_tahunan(s: pd.DataFrame) -> str:
    ada = s.loc[s["periode"].astype(str).str.fullmatch(r"\d{4}"), "jenis_periode"].dropna()
    return ada.mode().iat[0] if len(ada) else "tahunan"


def _wdi_dari_mentah(s: pd.DataFrame, kode_nas) -> pd.DataFrame:
    """Jalan keluar bila Silver tidak memuat WDI: baca ulang dari pembaca ekstraksi."""
    from src.ekstraksi.pembaca_wdi import baca_wdi_json
    w = baca_wdi_json()
    kurang = {"indicator_id", "date", "value", "_berkas_raw", "_sha256_raw"} - set(w.columns)
    if kurang:
        raise ValueError(f"Kolom WDI tidak ditemukan: {sorted(kurang)}; kolom ada: {list(w.columns)}")
    for kunci, nilai in (("countryiso3code", "IDN"), ("country_id", "ID")):
        if kunci in w.columns and w[kunci].notna().any():
            w = w[w[kunci] == nilai]
            break
    n0 = len(w)
    w = w[w["value"].notna()]
    print(f"    WDI dari data mentah (Silver tidak memuat WDI): {len(w)} dari {n0} baris bernilai")
    return pd.DataFrame({
        "seri_kode": w["indicator_id"].values,
        "periode": w["date"].astype(str).values,
        "jenis_periode": _label_tahunan(s),
        "rincian": TOTAL,
        "wilayah_kode": kode_nas,
        "nilai_nasional": pd.to_numeric(w["value"]).values,
        "satuan": "persen",
        "sumber": "wdi",
        "asal_nilai": "pembanding",
        "_berkas_raw": w["_berkas_raw"].values,
        "_sha256_raw": w["_sha256_raw"].values,
    })


def _cek_lineage(t: pd.DataFrame) -> None:
    manifest = baca(RAW)
    if t["_berkas_raw"].isna().any() or t["_sha256_raw"].isna().any():
        raise ValueError("Ada baris tanpa _berkas_raw atau _sha256_raw")
    asing = sorted(set(t["_berkas_raw"]) - set(manifest))
    if asing:
        raise ValueError(f"_berkas_raw di luar MANIFEST: {asing}")
    beda = t["_sha256_raw"] != t["_berkas_raw"].map(manifest)
    if beda.any():
        raise ValueError(f"{int(beda.sum())} baris dengan _sha256_raw berbeda dari MANIFEST")


def bangun_tabel_nasional(silver=None, tulis: bool = True) -> pd.DataFrame:
    s = _muat_silver(silver)
    kode_nas = _kode_nasional(s)
    print("--> Tabel nasional Gold")
    bagian = [_utama(s, kode_nas)]
    bagian += [_pembanding_silver(s, seri, kode_nas) for seri in PEMBANDING_ILO]
    if s["seri_kode"].isin(PEMBANDING_WDI).any():
        bagian += [_pembanding_silver(s, seri, kode_nas) for seri in PEMBANDING_WDI]
    else:
        bagian.append(_wdi_dari_mentah(s, kode_nas))

    t = pd.concat(bagian, ignore_index=True)
    hilang = [x for x in (UTAMA, *PEMBANDING_ILO, *PEMBANDING_WDI) if x not in set(t["seri_kode"])]
    if hilang:
        raise ValueError(f"Seri tanpa baris di tabel nasional: {hilang}")
    kembar = t.duplicated(["seri_kode", "periode"], keep=False)
    if kembar.any():
        raise ValueError(f"{int(kembar.sum())} baris berkunci (seri_kode, periode) kembar, contoh: "
                         f"{t.loc[kembar, ['seri_kode', 'periode']].head(3).values.tolist()}")
    _cek_lineage(t)

    t = t[KOLOM].sort_values(["seri_kode", "periode"]).reset_index(drop=True)
    print(t.groupby(["seri_kode", "asal_nilai", "rincian"]).agg(
        baris=("periode", "size"), dari=("periode", "min"), sampai=("periode", "max")).to_string())
    if tulis:
        GOLD.mkdir(parents=True, exist_ok=True)
        t.to_parquet(KELUARAN, index=False)
        t.to_csv(KELUARAN.with_suffix(".csv"), index=False)
        print(f"Tabel nasional tersimpan di {KELUARAN} ({len(t)} baris)")
    return t


# ---------------------------------------------------------------- uji
def uji_sintetis():
    def r(seri, w, p, jp, rinc, v, sumber="x"):
        return dict(sumber=sumber, seri_kode=seri, wilayah_kode=w, nama_wilayah="n", periode=p,
                    jenis_periode=jp, rincian=rinc, nilai=v, satuan="persen",
                    _berkas_raw="a", _sha256_raw="h")
    s = pd.DataFrame([
        r(UTAMA, 9999, "2005-02", "bulanan", "total", 10.0),
        r(UTAMA, 9999, "2005-08", "bulanan", "total", 11.0),
        r(UTAMA, 1100, "2005-02", "bulanan", "total", 12.0),
        r(UTAMA, 1100, "2006-02", "bulanan", "total", 13.0),       # provinsi tanpa baris Indonesia
        r(UTAMA, 9999, "2005-02", "bulanan", "perempuan", 14.0),   # bukan total
        r("UNE_DEAP_SEX_AGE_RT", 9999, "2020-Q3", "triwulanan", RINCIAN_TOTAL["UNE_DEAP_SEX_AGE_RT"], 4.5),
        r("UNE_DEAP_SEX_AGE_RT", 9999, "2020-Q3", "triwulanan", "perempuan", 5.0),
        r("SDG_0852_SEX_AGE_RT", 9999, "2020", "tahunan", "perempuan", 3.0),   # tidak punya total
    ])
    u = _utama(s, 9999)
    assert len(u) == 2 and set(u["nilai_nasional"]) == {10.0, 11.0}
    assert set(u["asal_nilai"]) == {"baris_indonesia"}
    p = _pembanding_silver(s, "UNE_DEAP_SEX_AGE_RT", 9999)
    assert len(p) == 1 and p["nilai_nasional"].iat[0] == 4.5 and p["asal_nilai"].iat[0] == "pembanding"
    try:
        _pembanding_silver(s, "SDG_0852_SEX_AGE_RT", 9999)
        raise AssertionError("seharusnya galat: tidak ada rincian total")
    except ValueError:
        pass
    print("[OK] Seri utama memakai baris Indonesia (total saja); pembanding berasal 'pembanding'; "
          "seri tanpa rincian total menghentikan proses.")


if __name__ == "__main__":
    if "--cek" in sys.argv:
        bangun_tabel_nasional(None, tulis=False)
    else:
        uji_sintetis()
