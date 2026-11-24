# Data Dictionary — Kasus 11: Tingkat Pengangguran Terbuka (SDG 8.5.2)

## 1. Skema Tabel Silver (`data/silver/silver.parquet`)
Tabel panjang terstandarisasi hasil ekstraksi, pembersihan, dan penyelarasan dari 14 berkas mentah (BPS, ILOSTAT, WDI) yang terdiri dari **7,495 baris**, **4 seri**, dan **39 wilayah**. *(Catatan: Kolom Gold akan ditambahkan pada Sprint 2–3).*

| Nama Kolom | Tipe Data | Satuan | Arti / Definisi | Asal (Berkas Mentah atau Keputusan di Log) |
| :--- | :--- | :--- | :--- | :--- |
| `sumber` | `str` | Tidak bersatuan (kategori) | Kode produsen atau penyedia data statistik asal (`bps`, `ilostat`, `wdi`). | Diturunkan dari struktur direktori `data/raw/<sumber>/...` sesuai keputusan penamaan sumber pada `log-keputusan.csv`. |
| `seri_kode` | `str` | Tidak bersatuan (kode) | Kode unik seri indikator pengangguran sesuai katalog masing-masing sumber (misalnya `var543`, `SL.UEM.TOTL.ZS`, `UNE_DEAP_SEX_AGE_RT`). | Diambil dari atribut kode indikator/variabel pada metadata maupun nama berkas di `data/raw/` (`manifest_asal.json`, `dataflow.json`, `sumber2_indikator.json`). |
| `wilayah_kode` | `int64` | Tidak bersatuan (kode numerik) | Kode wilayah geografis baku: `9999` untuk agregat nasional Indonesia, dan kode provinsi BPS 2 digit dikali `100` (susunan 38 provinsi, misal `1100` untuk Aceh). | Hasil pemetaan kode wilayah sumber mentah (`kode_wilayah` BPS / kode ISO3 `IDN` pada WDI & ILOSTAT) berdasarkan aturan kodifikasi wilayah pada `log-keputusan.csv`. |
| `nama_wilayah` | `str` | Tidak bersatuan (teks) | Nama resmi wilayah administrasi dalam bahasa Indonesia (contoh: `Indonesia`, `Aceh`, `Sumatera Utara`). | Diselaraskan dari label wilayah pada berkas mentah menggunakan kamus referensi 38 provinsi + nasional di `src/silver/` (`log-keputusan.csv`). |
| `periode` | `str` | Tidak bersatuan (format waktu ISO/baku) | Label waktu pengamatan terstandarisasi sesuai frekuensi data (contoh: `2000` untuk tahunan, `2005-02` untuk bulanan, `2008-Q1` untuk triwulanan). | Diformat ulang dari kolom tahun/bulan/triwulan pada berkas mentah BPS, WDI, dan ILOSTAT mengikuti standar format waktu pada `log-keputusan.csv`. |
| `jenis_periode` | `str` | Tidak bersatuan (kategori) | Tingkat agregasi atau frekuensi waktu pengamatan (`tahun`, `semester`, `triwulan`, `bulan`). | Ditentukan dari pola granulasi waktu setiap berkas sumber pada tahap pembersihan Silver (`log-keputusan.csv`). |
| `rincian` | `str` | Tidak bersatuan (kategori) | Dimensi disagregasi populasi angkatan kerja (misalnya `total`, kelompok umur seperti `15-24`, atau jenis kelamin/disabilitas). | Dipetakan dari dimensi rincian pada berkas mentah BPS dan struktur dimensi DSD ILOSTAT (`dsd/*.json`) sesuai keputusan penyeragaman label di `log-keputusan.csv`. |
| `nilai` | `float64` | `persen` | Angka Tingkat Pengangguran Terbuka (TPT), yaitu persentase jumlah penganggur terhadap total angkatan kerja (rentang valid `0` s.d. `100`). | Diambil langsung dari kolom nilai pengamatan (`val`/`value`/`OBS_VALUE`) di berkas mentah setelah pembersihan karakter non-numerik (`log-keputusan.csv`). |
| `satuan` | `str` | `persen` | Satuan pengukuran nilai pengamatan yang diseragamkan ke bentuk baku (`persen`). | Dikonversi dan diseragamkan dari label satuan mentah (`%`, `Persen`, `Percent`) berdasarkan keputusan standarisasi satuan di `log-keputusan.csv`. |
| `_berkas_raw` | `str` | Tidak bersatuan (jalur berkas) | Jalur relatif berkas data mentah asal baris tersebut di dalam direktori `data/raw/`. | Dicatat otomatis oleh tahap ekstraksi (`src/ekstraksi/`) saat membaca setiap berkas sumber dari `data/raw/`. |
| `_sha256_raw` | `str` | Tidak bersatuan (hash heksadesimal 64 karakter) | Sidik kriptografis SHA-256 dari berkas mentah yang dirujuk oleh `_berkas_raw` untuk menjamin integritas dan reprodusibilitas. | Dihitung oleh modul ekstraksi dari isi biner berkas mentah dan dicocokkan terhadap `data/raw/MANIFEST.csv`. |

---

## 2. Contoh Penelusuran Satu Baris Silver ke Berkas Mentah (*Data Lineage*)

Berikut adalah bukti penelusuran satu baris aktual dari `data/silver/silver.parquet` (baris indeks `0`) hingga ke berkas mentah asalnya di `data/raw/`:

### A. Isi Baris pada `data/silver/silver.parquet`
- **`sumber`**: `bps`
- **`seri_kode`**: `var543`
- **`wilayah_kode`**: `1100`
- **`nama_wilayah`**: `ACEH`
- **`periode`**: `2000`
- **`jenis_periode`**: `tahun`
- **`rincian`**: `total`
- **`nilai`**: `4.8`
- **`satuan`**: `persen`
- **`_berkas_raw`**: `bps/2026-10-17/sdg8_tpt.csv`
- **`_sha256_raw`**: `9d902bc126481bafd20b4429f7381944ca0ba7e363f08d697fd15149d4c3faa2`

### B. Verifikasi terhadap Berkas Mentah & `MANIFEST.csv`
1. Berdasarkan kolom `_berkas_raw`, baris di atas berasal dari berkas mentah:
   `data/raw/bps/2026-10-17/sdg8_tpt.csv`
2. Ketika dihitung ulang sidik kriptografisnya menggunakan perintah `sha256sum data/raw/bps/2026-10-17/sdg8_tpt.csv`, dihasilkan nilai hash:
   `9d902bc126481bafd20b4429f7381944ca0ba7e363f08d697fd15149d4c3faa2`
3. Nilai hash tersebut **identik (`True`)** dengan nilai kolom `_sha256_raw` pada baris Silver (`9d902bc126481bafd20b4429f7381944ca0ba7e363f08d697fd15149d4c3faa2`) serta catatan pada `data/raw/MANIFEST.csv`, sehingga asal-usul dan keaslian angka `nilai = 4.8 persen` pada periode `2000` dapat dibuktikan secara penuh.
