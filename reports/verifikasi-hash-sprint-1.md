# Laporan Verifikasi Data & Konsistensi Hash (Sprint 1)

**Penanggung Jawab:** Muhammad Fathiy Zumar Yazid (124450081)
**Tanggal Verifikasi:** 12 November 2026
**Kasus:** 11 - Pengangguran Terbuka

## 1. Hasil Pemeriksaan SHA256 Paket Data (`data/raw/`)
Seluruh anggota telah menjalankan perintah `python unduh_data.py --kasus 11` di laptop masing-masing. Berikut adalah bukti komentar/laporan dari anggota bahwa pemeriksaan sha256 berstatus **LOLOS**:

| No | Nama Anggota | NIM | Status SHA256 | Bukti / Catatan |
|----|--------------|-----|---------------|-----------------|
| 1  | MUHAMMAD FATHIY ZUMAR YAZID | 124450081 | ✅ LOLOS | Output terminal sukses, 14 berkas utuh. |
| 2  | BRYAN PASKAH TELAUMBANUA | 124450003 | ✅ LOLOS | Output terminal sukses, 14 berkas utuh. |
| 3  | RAFLI AL MANSYAH TAMBUNAN | 124450007 | ✅ LOLOS | Output terminal sukses, 14 berkas utuh. |
| 4  | HAIKAL SEVENTINO TAMBA | 124450012 | ✅ LOLOS | Output terminal sukses, 14 berkas utuh. |
| 5  | AYAKE ALFATIH RAMADAN | 124450108 | ✅ LOLOS | Output terminal sukses, 14 berkas utuh. |

*(Catatan: Saya juga telah memastikan bahwa folder `data/raw/` tidak pernah masuk ke dalam Git / ter-commit, sesuai aturan integritas data).*

## 2. Konsistensi `data_hash` di `results/<nim>/metrics.json`
Karena `data_hash` dihitung otomatis dari `MANIFEST.csv`, nilai ini **wajib sama** untuk semua anggota. Berikut adalah hasil pengecekan dari file `metrics.json` masing-masing anggota:

| NIM | `data_hash` | Status |
|-----|-------------|--------|
| 124450081 | `56ae001b3cc5d23542383f99e52b63b5c5ad78d379edb030a09adcf4ca3bbb76` | ✅ SAMA |
| 124450003 | `56ae001b3cc5d23542383f99e52b63b5c5ad78d379edb030a09adcf4ca3bbb76` | ✅ SAMA |
| 124450007 | `56ae001b3cc5d23542383f99e52b63b5c5ad78d379edb030a09adcf4ca3bbb76` | ✅ SAMA |
| 124450012 | `56ae001b3cc5d23542383f99e52b63b5c5ad78d379edb030a09adcf4ca3bbb76` | ✅ SAMA |
| 124450108 | `56ae001b3cc5d23542383f99e52b63b5c5ad78d379edb030a09adcf4ca3bbb76` | ✅ SAMA |

**Kesimpulan:** Seluruh anggota menggunakan paket data mentah yang identik (tidak ada yang rusak atau termodifikasi). Pekerjaan siap dilanjutkan ke tahap ekstraksi Silver.