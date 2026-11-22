\# Alasan Pemilihan Basis Data (Tahap 5)



\## 1. SQLite untuk Lapis Silver

\- \*\*Alasan\*\*: SQLite ringan, tidak memerlukan server, dan sangat cocok untuk menyimpan data baris demi baris (row-oriented) seperti tabel panjang (long format) di Silver.

\- \*\*Kunci Primer\*\*: `(sumber, seri\_kode, wilayah\_kode, periode, rincian, \_berkas\_raw)`.



\## 2. DuckDB untuk Lapis Gold

\- \*\*Alasan\*\*: DuckDB adalah basis data kolumnar (column-oriented) yang dioptimalkan untuk analitik dan agregasi. Sangat cepat untuk membentuk panel (provinsi × periode × indikator) dibandingkan SQLite atau PostgreSQL.

\- \*\*Kunci Primer\*\*: `(wilayah\_kode, periode, indikator)`.



\## 3. Perbandingan dengan Menyimpan JSON Mentah

\- Menyimpan respons JSON mentah (seperti di `data/raw/`) bagus untuk arsip (Bronze), tetapi sangat buruk untuk analisis deret waktu. Query SQL pada JSON akan sangat lambat dan rawan error.

\- Memuat ke SQL (Silver/Gold) memungkinkan validasi tipe data, penegakan kunci primer (mencegah duplikat), dan eksekusi query yang cepat.

