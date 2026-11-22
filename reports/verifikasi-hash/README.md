# Verifikasi hash data mentah

Laporan terbaru: [sprint-1.md](sprint-1.md), dihasilkan otomatis
oleh `tools/verifikasi_hash.py`, bukan diketik tangan.

## Cara mengulang
python unduh_data.py --kasus 11
python tools/verifikasi_hash.py lokal --nim <NIM>
git fetch --all --prune
python tools/verifikasi_hash.py tim

Exit code 0 berarti semua anggota lolos dan data_hash seragam.

## Catatan integritas
- `data/raw/` ada di `.gitignore`.
- `git log --all -- data/raw` kosong (tidak pernah di-commit).
- Hash dibaca dari `results/<nim>/metrics.json` di cabang
  `<nim>/kerja` tiap anggota; SHA commit tercatat di laporan.
- Bukti sha256 per berkas: `results/<nim>/bukti_sha256.json`.
- Tidak ada artefak pengganti berlabel umum di `results/`.
