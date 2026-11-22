#!/usr/bin/env python
"""Verifikasi data mentah dan konsistensi data_hash (tugas penjaga data).

Dijalankan dari root repo:
  python tools/verifikasi_hash.py lokal --nim <NIM>   # bukti sha256 per anggota
  python tools/verifikasi_hash.py tim                 # laporan tim (exit 0 bila lolos)
"""
import argparse, csv, hashlib, json, platform, subprocess, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAW = Path("data/raw")
PENJAGA = "124450081"
ANGGOTA = ["124450081", "124450003", "124450007", "124450012", "124450108"]
BUKAN_ARTEFAK = {".gitkeep", "README.md"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def baca_manifest():
    with open(RAW / "MANIFEST.csv", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        kol = rd.fieldnames
        k_sha = next(k for k in kol if "sha" in k.lower())
        k_path = next((k for k in kol if any(t in k.lower()
                       for t in ("path", "jalur", "berkas", "file", "nama"))), kol[0])
        return [(r[k_path], r[k_sha].strip().lower()) for r in rd]


def git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8")


def lokal(nim: str):
    hasil, ok = [], 0
    for rel, sha_manifest in baca_manifest():
        p = RAW / rel
        sha_hitung = sha256_file(p) if p.exists() else None
        cocok = sha_hitung == sha_manifest
        ok += cocok
        hasil.append({"berkas": rel, "sha256_manifest": sha_manifest,
                      "sha256_dihitung": sha_hitung, "cocok": cocok})
    bukti = {
        "nim": nim,
        "waktu_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "perangkat": f"{platform.system()} {platform.machine()} Python {platform.python_version()}",
        "sha256_MANIFEST.csv": sha256_file(RAW / "MANIFEST.csv"),
        "berkas_total": len(hasil), "berkas_cocok": ok,
        "lolos": ok == len(hasil), "rincian": hasil,
    }
    out = Path("results") / nim / "bukti_sha256.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bukti, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{ok}/{len(hasil)} berkas cocok -> {out}")
    sys.exit(0 if bukti["lolos"] else 1)


def baca_dari_git(nim: str, nama: str):
    """Baca results/<nim>/<nama> dari cabang anggota. Kembalikan (data, ref, commit)."""
    refs = [f"origin/{nim}/kerja", "origin/main"]
    if nim == PENJAGA:
        refs.append("HEAD")          # bukti penjaga ada di cabang revisi ini
    for ref in refs:
        c = git("rev-parse", "--short", ref)
        if c.returncode != 0:
            continue
        s = git("show", f"{ref}:results/{nim}/{nama}")
        if s.returncode == 0:
            return json.loads(s.stdout), ref, c.stdout.strip()
    return None, None, None


def tim():
    git("fetch", "--all", "--prune")
    data = []
    for nim in ANGGOTA:
        m, ref, commit = baca_dari_git(nim, "metrics.json")
        b, _, _ = baca_dari_git(nim, "bukti_sha256.json")
        data.append((nim, m, ref, commit, b))

    hashes = Counter(m["data_hash"] for _, m, *_ in data if m)
    acuan = hashes.most_common(1)[0][0] if hashes else ""

    baris = []
    for nim, m, ref, commit, b in data:
        if m is None:
            baris.append(f"| {nim} | (tidak ditemukan) | - | - | - | BELUM ADA |")
            continue
        h = m.get("data_hash", "")
        sha = "lolos" if b and b.get("lolos") else "belum ada bukti"
        baris.append(f"| {nim} | `{h}` | `{ref}` | `{commit}` | {sha} | "
                     f"{'SAMA' if h == acuan else 'BEDA'} |")

    aneh = []
    for p in git("ls-files", "results").stdout.splitlines():
        bagian = p.split("/")
        if Path(p).name in BUKAN_ARTEFAK:
            continue
        if len(bagian) < 3 or bagian[1] not in ANGGOTA:
            aneh.append(p)

    lap = ["# Laporan verifikasi hash (dihasilkan otomatis)",
           f"Dibuat: {datetime.now(timezone.utc).isoformat(timespec='seconds')} UTC",
           "Diulang dengan: `python tools/verifikasi_hash.py tim`", "",
           "| NIM | data_hash | Sumber | Commit | sha256 lokal | Status |",
           "|---|---|---|---|---|---|", *baris, "",
           f"Jumlah nilai data_hash berbeda: **{len(hashes)}**",
           f"Artefak di luar results/<nim>/: {aneh if aneh else 'tidak ada'}"]
    out = Path("reports/verifikasi-hash/sprint-1.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lap), encoding="utf-8")
    print("\n".join(lap))

    lengkap = all(m for _, m, *_ in data)
    bukti_ok = all(b and b.get("lolos") for *_, b in data)
    sys.exit(0 if len(hashes) == 1 and lengkap and bukti_ok and not aneh else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("lokal")
    a.add_argument("--nim", required=True)
    sp.add_parser("tim")
    arg = ap.parse_args()
    lokal(arg.nim) if arg.cmd == "lokal" else tim()
