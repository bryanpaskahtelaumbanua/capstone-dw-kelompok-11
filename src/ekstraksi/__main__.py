from src.ekstraksi import cetak_laporan, ekstrak

r = ekstrak()
cetak_laporan(r)
m = r["metrik"]
print("\nPerintah metrik (ganti <NIM> dengan NIM Anda):")
print(f"python -m src.common.hasil <NIM> berkas_dibaca={m['berkas_dibaca']} "
      f"baris_mentah={m['baris_mentah']} baris_metadata={m['baris_metadata']} format={m['format']}")