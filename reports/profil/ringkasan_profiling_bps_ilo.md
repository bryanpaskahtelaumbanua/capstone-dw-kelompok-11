# Profiling missing, outlier, dan duplikat: seri utama BPS dan ILO

Hanya menemukan dan menandai; tidak ada nilai di `data/raw/` yang diubah. Setiap calon dapat ditelusuri lewat `berkas_raw`, `baris_csv`, dan `sha256_raw` di berkas CSV masing-masing.

## BPS var543 (rinci di tugas #12 dan #13)

- baris_mentah: 2000
- kunci_kembar: 0
- baris_identik_penuh: 0
- obs_kosong: 0

## ILOSTAT

| Seri | Baris | Deret rincian | Obs kosong | Kunci kembar | Identik penuh | Deret bercelah | Periode celah | Calon anomali | Bertepatan patahan |
|---|---|---|---|---|---|---|---|---|---|
| SDG_0852_SEX_AGE_RT | 216 | 9 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| SDG_0852_SEX_DSB_RT | 81 | 9 | 3 | 0 | 0 | 9 | 48 | 5 | 0 |
| UNE_DEAP_SEX_AGE_RT | 5424 | 168 | 223 | 0 | 0 | 167 | 2946 | 96 | 17 |

Definisi: *celah* = periode yang hilang di antara periode pertama dan terakhir deret rincian itu (missing aktual). Periode sebelum deret mulai atau sesudah berakhir bukan missing (struktural). *Calon anomali* = sisa terhadap median lokal (5 periode; data kuartalan: selisih dengan kuartal sama tahun lalu) di luar 1,5 x IQR, atau lonjakan dengan z-robust >= 3.5; keduanya hanya ditandai bila selisihnya >= max(1.0 poin, 15% dari median deret).
