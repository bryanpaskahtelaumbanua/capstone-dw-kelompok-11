# Laporan tim — Kelompok 11_DW_RB, Kasus 11 Pengangguran Terbuka (SDG 8.5.2)

Satu dokumen bersama, enam bagian. Angka harus dapat ditarik ulang dari `data/silver`, `data/gold`,
dan `log-keputusan.csv` yang sudah di-*commit*.

## Ringkasan
Kasus 11 menganalisis indikator Tingkat Pengangguran Terbuka (SDG 8.5.2) pada seri utama BPS (`var543`, 38 provinsi dan nasional, 1986–2026-02) serta 5 seri pembanding nasional dari WDI dan ILOSTAT (`SL.UEM.TOTL.ZS`, `SL.UEM.TOTL.NE.ZS`, `SDG_0852_SEX_AGE_RT`, `SDG_0852_SEX_DSB_RT`, `UNE_DEAP_SEX_AGE_RT`). Seluruh 14 berkas mentah tervalidasi SHA-256 dan diseragamkan menjadi 7.572 baris observasi valid pada lapisan Silver (`data/silver/silver.parquet`).

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
*(Draf — dilengkapi pada Sprint 2 bersama komponen Integrasi)*

## Validasi dan reproduksibilitas
*(Draf — dilengkapi pada Sprint 2–3 bersama komponen Validasi)*

## Pembagian kerja
| Anggota | NIM | Komponen | Tugas sampingan | Bagian laporan yang ditulis |
|---|---|---|---|---|
| Bryan Paskah Telaumbanua | 124450003 | Ekstraksi dan lineage | Koordinator | Data dan lineage |
| Muhammad Fathiy Zumar Yazid | 124450081 | Profil dan pembersihan | Penjaga Data & Evaluasi | Masalah data dan penanganannya (profil & anomali) |
| Ayake Alfatih Ramadan | 124450108 | Transformasi dan panel | Analis Utama | Masalah data dan penanganannya (transformasi & katalog), Analisis panel |
| Rafli Al Mansyah Tambunan | 124450007 | Integrasi, penyimpanan, dan skala | Integrator | Integrasi dan rekonsiliasi |
| Haikal Seventino Tamba | 124450012 | Validasi dan dokumentasi | Reproduksi & Demo | Validasi dan reproduksibilitas |
