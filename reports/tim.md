# Laporan tim — Kelompok 11_DW_RB, Kasus 11 Pengangguran Terbuka (SDG 8.5.2)

Satu dokumen bersama, enam bagian. Angka harus dapat ditarik ulang dari `data/silver`, `data/gold`,
dan `log-keputusan.csv` yang sudah di-*commit*.

## Ringkasan
Kasus 11 menganalisis indikator Tingkat Pengangguran Terbuka (SDG 8.5.2) pada seri utama BPS (`var543`, 38 provinsi dan nasional, 1986–2026-02) serta 5 seri pembanding nasional dari WDI dan ILOSTAT (`SL.UEM.TOTL.ZS`, `SL.UEM.TOTL.NE.ZS`, `SDG_0852_SEX_AGE_RT`, `SDG_0852_SEX_DSB_RT`, `UNE_DEAP_SEX_AGE_RT`). Seluruh 14 berkas mentah tervalidasi SHA-256 dan diseragamkan menjadi 7.495 baris observasi valid pada lapisan Silver (`data/silver/silver.parquet`).

## Data dan lineage
*(Draf — dilengkapi pada Sprint 2–3 bersama komponen Ekstraksi)*

## Masalah data dan penanganannya

| ID Log | Kategori Masalah | Seri Terdampak | Temuan & Jumlah Terdampak | Keputusan Penanganan | Alternatif yang Ditolak |
|---|---|---|---|---|---|
| `K-001` | Pemekaran wilayah | Semua (`var543`) | Perubahan jumlah provinsi sejak 1986 hingga susunan 38 provinsi tahun 2025 (`1100` s.d. `9700`). | Menyeragamkan kode wilayah ke susunan 38 provinsi tahun 2025; provinsi pemekaran memakai data sejak tahun berdiri dan provinsi induk dibiarkan apa adanya. | Menggabungkan provinsi baru ke induk dengan bobot penduduk atau membuang provinsi pemekaran. |
| `K-002` | Granularitas level & periode campur | `var543` | Terdapat 61 baris agregat nasional (`9999` Indonesia) tercampur dengan 1.939 baris provinsi, serta periode campur (`Tahunan`, `Februari`, `Agustus`). | Memisahkan baris nasional (`9999`) dari grid 38 provinsi dan mempertahankan periode asli (`YYYY`, `YYYY-02`, `YYYY-08`) di Silver tanpa merata-ratakan. | Menggabungkan baris nasional ke grid provinsi atau merata-ratakan Februari dan Agustus menjadi tahunan di Silver. |
| `K-003` | Kekosongan struktural vs *missing* | `var543` | Dari 379 sel kosong pada grid 38 provinsi × periode, 378 sel merupakan kekosongan struktural sebelum provinsi pemekaran berdiri atau sebelum seri terbit. | Membedakan kekosongan struktural (belum terbentuk/terbit) dari *missing value* operasional dan hanya menyimpan observasi valid di Silver. | Menganggap seluruh 379 sel kosong pada grid sebagai *missing value* seragam. |
| `K-004` | Ketidaksesuaian satuan & kode SDG | Semua (6 seri) | Satuan mentah berbeda antar-sumber (`Persen` BPS, `PT` ILOSTAT, `None` WDI) serta kode SDG WDI kosong (`—`) di katalog awal (7.572 baris). | Menyeragamkan seluruh satuan menjadi `persen` dan menetapkan kode SDG `8.5.2` pada `SL.UEM.TOTL.ZS` dan `SL.UEM.TOTL.NE.ZS` sesuai metadata WDI. | Membiarkan satuan heterogen atau membiarkan kode SDG kosong di katalog. |
| `K-005` | Duplikasi format sumber BPS | `var543` | Berkas `sdg8_tpt.csv` (2.000 baris) dan `json/sdg8_tpt.json` (2.000 baris) terbukti 100% identik (0 selisih nilai maupun periode). | Menggunakan berkas CSV BPS terstruktur sebagai sumber Silver (`bps/2026-10-17/sdg8_tpt.csv`) sehingga mengeliminasi 2.000 baris duplikat JSON. | Memuat kedua format CSV dan JSON BPS sekaligus ke tabel Silver. |
| `K-006` | Encoding dimensi, triwulan, & nilai null | Seri ILOSTAT & WDI | Rincian dimensi `SEX`, `AGE`, dan `DSB` ILOSTAT belum ter-encode (94 kombinasi unik di Silver), frekuensi tahunan (`A`) bercampur triwulanan (`Q`), serta terdapat 281 observasi bernilai `null`. | Meng-encode dimensi rincian (`SEX|AGE` dan `SEX|DSB`), memisahkan format `tahun` (`YYYY`) dan `triwulan` (`YYYY-Q1..Q4`), serta membuang 281 baris `null` sesuai skema Silver. | Mengabaikan rincian dimensi (menyebabkan bentrok kunci unik Silver) atau menyimpan nilai `null`. |

*Catatan deteksi anomali (`reports/profil/daftar_calon_anomali.csv`): ditemukan 79 calon anomali pada `var543` berdasarkan metode IQR dan Z-score (ditandai pada tahap profil tanpa mengubah nilai mentah, untuk diklasifikasikan lebih lanjut pada tahap pembersihan dan rekonsiliasi).*

## Integrasi dan rekonsiliasi
*(Draf — Kartu #33, disusun dari `data/silver/silver.parquet` [7.495 baris], `data/gold/panel.parquet` [1.939 baris, 38 provinsi], dan berkas mentah terverifikasi SHA-256)*

### 1. Skema Integrasi Lapisan Gold dan Kunci Penggabungan
Integrasi pada lapisan Gold memisahkan secara ketat dua tingkat granularitas agar tidak terjadi agregasi ganda maupun percampuran unit analisis:
1. **Panel Provinsi (`data/gold/panel.parquet` — Kartu #26)**: Dibentuk dari seri utama BPS `var543` tingkat provinsi (`wilayah_kode != 9999`, 38 provinsi susunan 2025) melalui operasi `.pivot()` ketat pada kunci unik `(wilayah_kode, nama_wilayah, periode)`. Sebanyak **1.939 baris** panel terbentuk (mempertahankan granularitas periode asli `YYYY` untuk 1986–2004 dan `YYYY-02`/`YYYY-08` untuk 2005–2026-02), dengan **5.556 baris** Silver lainnya (61 baris nasional `9999` dan 5.495 baris pembanding WDI/ILOSTAT) dikeluarkan sesuai keputusan `K-023`. Setiap sel Gold mempertahankan jejak ketelusuran 1:1 ke Silver melalui `_berkas_raw` dan `_sha256_raw` serta penanda anomali Sprint 1 (`1.862` normal, `75` `outlier_asli`, `2` `patahan_seri`).
2. **Tabel Nasional & Rekonsiliasi (`wilayah_kode = 9999` / `IDN`)**: Baris agregat Indonesia dari BPS (`var543`, 61 baris: 18 tahunan `1986`–`2004` dan 43 bulanan `2005-02`–`2026-02`) diseragamkan kuncinya (`9999` dipetakan ke `IDN` dan dimensi waktu diselaraskan ke tahun kalender `YYYY` pada `outer join`) untuk dibandingkan dengan 5 seri pembanding nasional dari WDI dan ILOSTAT tanpa membuang periode yang hanya muncul di salah satu sumber (`left_only` / `right_only`).

### 2. Ringkasan Empat Pasangan Rekonsiliasi Utama (`P1`–`P4`)

| Pasangan | Seri Utama (BPS) | Seri Pembanding | Periode Tumpang Tindih | Selisih Median (`BPS - Pembanding`) | Rentang Selisih (`Min` s.d. `Maks`) | Kategori Penjelasan Utama |
|---|---|---|---|---|---|---|
| **P1** | `var543` (`9999`, Tahunan `1986`–`2004` & Agustus `2005`–`2023`) | WDI `SL.UEM.TOTL.NE.ZS` *(estimasi nasional)* | 36 tahun (`1986`–`2023`) | **+1,5830 pp** | `-0,0060` s.d. `+3,2950 pp` | `definisi berbeda`, `metode berbeda` |
| **P2** | `var543` (`9999`, Tahunan `1986`–`2004` & Agustus `2005`–`2025`) | WDI `SL.UEM.TOTL.ZS` *(estimasi model ILO)* | 34 tahun (`1991`–`2025`) | **+1,6510 pp** | `-0,0060` s.d. `+3,2950 pp` | `definisi berbeda`, `metode berbeda`, `vintage berbeda` |
| **P3** | `var543` (`9999`, Tahunan `2000`–`2004` & Agustus `2005`–`2023`) | ILOSTAT `SDG_0852_SEX_AGE_RT` (`SEX_T\|AGE_YTHADULT_YGE15`) | 24 tahun (`2000`–`2023`) | **+1,8625 pp** | `+0,0020` s.d. `+3,2950 pp` | `definisi berbeda`, `cakupan berbeda` |
| **P4** | *(Tidak ada padanan BPS di paket)* | ILOSTAT `SDG_0852_SEX_DSB_RT` *(konteks disabilitas)* | 14 tahun (`2010`–`2023`, 78 baris Silver) | *Tidak dihitung* | *Konteks disparitas* | `tanpa pasangan` |

### 3. Penjelasan Selisih dan Pemetaan Periode Survei
1. **Perbedaan Definisi Operasional (`definisi berbeda` & `metode berbeda`)**: Pada tahun `2000`, angka BPS (`6,08%`) dan ILOSTAT `SDG_0852_SEX_AGE_RT` (`6,078%`) praktis identik (selisih pembulatan `+0,0020 pp`). Namun sejak `2001` hingga `2023`, angka BPS secara konsisten lebih tinggi (median `+1,8625 pp` terhadap ILOSTAT dan `+1,5830 pp` terhadap WDI nasional) karena konsep Tingkat Pengangguran Terbuka nasional Sakernas BPS mencakup penduduk yang tidak aktif mencari kerja karena merasa tidak mungkin mendapat pekerjaan (*discouraged workers*) serta yang sudah diterima bekerja tetapi belum mulai bekerja, sedangkan harmonisasi standar ILO menerapkan kriteria pencarian kerja aktif dan kesiapan bekerja yang lebih ketat.
2. **Perbandingan Dua Versi WDI (`P1` vs `P2`)**: Antara seri estimasi nasional `SL.UEM.TOTL.NE.ZS` dan estimasi model ILO `SL.UEM.TOTL.ZS`, median selisih pada 32 tahun tumpang tindih (`1991`–`2023`) adalah **0,0000 pp** dengan deviasi absolut maksimum hanya **0,1160 pp**, sehingga keduanya konsisten merepresentasikan deret harmonisasi ILO. 
3. **Konsekuensi Bulan Survei (`P3`)**: BPS menerbitkan survei semesteran Februari (`YYYY-02`) dan Agustus (`YYYY-08`) sejak `2005`, sedangkan ILOSTAT menerbitkan satu angka tahunan (`YYYY`). Uji perbandingan menunjukkan selisih median `BPS Agustus - ILOSTAT` sebesar **+1,7640 pp** (`2005`–`2023`, 19 tahun), sedikit lebih besar daripada `BPS Februari - ILOSTAT` (**+1,6900 pp**). Pada tabel rekonsiliasi, bulan survei BPS dicatat eksplisit (`periode_bps`) dan selisihnya **tidak dihapus maupun disamakan paksa**, melainkan dilabeli dengan kategori baku (`definisi berbeda`, `metode berbeda`, `vintage berbeda`, `cakupan berbeda`, `belum terjelaskan`, atau `tanpa pasangan`).
4. **Konteks Disabilitas (`P4`)**: Seri `SDG_0852_SEX_DSB_RT` (78 baris di Silver, mencakup 9 kombinasi `SEX` $\times$ `DSB_STATUS`) menjadi indikator kontekstual karena paket BPS `var543` tidak memuat rincian status disabilitas. Pada tahun `2023`, TPT total penduduk disabilitas (`SEX_T|DSB_STATUS_DIS`) tercatat **3,352%**, sedikit di bawah penduduk non-disabilitas (`SEX_T|DSB_STATUS_NODIS` = **3,424%**).

### 4. Alasan Pemilihan Basis Data (JSON vs SQL)
Pada tahap penyimpanan, kami memilih menyimpan data ke dalam basis data SQL (SQLite untuk lapis Silver, DuckDB untuk lapis Gold) dengan alasan sebagai berikut:
1. **Integritas Data:** SQL memungkinkan penerapan kunci primer (primary key) yang mencegah duplikasi data secara otomatis, dan validasi tipe data (tipe kolom yang jelas).
2. **Performa Analitik:** Untuk keperluan agregasi panel dan rekonsiliasi, DuckDB (yang bersifat kolumnar) mengeksekusi query jauh lebih cepat dibandingkan membaca file Parquet atau JSON secara langsung.
3. **Perbandingan dengan JSON Mentah:** Menyimpan respons JSON mentah di folder `data/raw/` (lapis Bronze) sangat penting untuk arsip agar struktur asli dari sumber (BPS, WDI, ILO) tetap utuh. Namun, JSON mentah sangat tidak efisien untuk analisis karena tidak memiliki skema yang kaku dan query-nya akan sangat lambat. Oleh karena itu, JSON disimpan sebagai arsip, sementara analisis dilakukan pada SQL.

## Validasi dan reproduksibilitas
*(Catatan Sprint 1 — dilengkapi kembali pada Sprint 2–3 setelah lapisan Gold selesai)*

- **Validasi Dasar Silver (`src/validasi/__init__.py`):** Telah diimplementasikan dan dijalankan terhadap `data/silver/silver.parquet` (7.495 baris, 4 seri, 39 wilayah) dengan hasil **5/5 aturan lolos** (kelengkapan 11 kolom wajib, rentang nilai `0–100`, kesesuaian format `periode` dengan `jenis_periode`, keunikan kunci komposit, dan konsistensi satuan `persen` per seri). Hasil metrik tersimpan di `results/124450012/metrics.json`.
- **Dokumentasi & Penelusuran Lineage (`docs/data-dictionary.md`):** Seluruh 11 kolom wajib tabel Silver telah didokumentasikan (nama, tipe data, satuan, arti, dan asal data), dilengkapi contoh verifikasi penelusuran satu baris aktual Silver hingga ke berkas mentahnya melalui `_berkas_raw` dan kecocokan sidik SHA-256 (`_sha256_raw`).
- **Rencana Sprint 2–3:** Menambahkan aturan validasi lapisan Gold (termasuk pencegahan tumpang tindih kelompok umur ILO dalam satu penjumlahan) serta melengkapi tabel kamus kolom Gold pada `docs/data-dictionary.md`.

## Pembagian kerja
| Anggota | NIM | Komponen | Tugas sampingan | Bagian laporan yang ditulis |
|---|---|---|---|---|
| Bryan Paskah Telaumbanua | 124450003 | Ekstraksi dan lineage | Koordinator | Data dan lineage |
| Muhammad Fathiy Zumar Yazid | 124450081 | Profil dan pembersihan | Penjaga Data & Evaluasi | Masalah data dan penanganannya (profil & anomali) |
| Ayake Alfatih Ramadan | 124450108 | Transformasi dan panel | Analis Utama | Masalah data dan penanganannya (transformasi & katalog), Analisis panel |
| Rafli Al Mansyah Tambunan | 124450007 | Integrasi, penyimpanan, dan skala | Integrator | Integrasi dan rekonsiliasi |
| Haikal Seventino Tamba | 124450012 | Validasi dan dokumentasi | Reproduksi & Demo | Validasi dan reproduksibilitas |