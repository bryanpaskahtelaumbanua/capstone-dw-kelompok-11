import json
from pathlib import Path
import pandas as pd
from src.common.manifest import sha256_raw

DATA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

def baca_bps_csv(berkas_relatif):
    path_lengkap = DATA_RAW / berkas_relatif
    
    nilai_sha256 = sha256_raw(berkas_relatif)
    
    df = pd.read_csv(path_lengkap, sep=None, engine='python', encoding='utf-8')
    
    df['_berkas_raw'] = str(berkas_relatif)
    df['_sha256_raw'] = nilai_sha256
    
    return df

def baca_bps_json(berkas_relatif):
    path_lengkap = DATA_RAW / berkas_relatif
    nilai_sha256 = sha256_raw(berkas_relatif)
    
    with open(path_lengkap, 'r', encoding='utf-8') as f:
        data_json = json.load(f)
    
    baris_tabel = []
    items = data_json if isinstance(data_json, list) else data_json.get('data', [data_json])
    
    for item in items:
        vervar = item.get('vervar', item.get('kode_wilayah', None))
        
        raw_turtahun = item.get('turvar', item.get('turtahun', 'Tahunan')) 
        
        jenis_periode = raw_turtahun 
        
        datacontent = item.get('datacontent', {})
        if isinstance(datacontent, dict):
            for thn, nilai in datacontent.items():
                baris_tabel.append({
                    'vervar': vervar,
                    'turtahun': raw_turtahun,
                    'jenis_periode': jenis_periode, 
                    'tahun': thn,
                    'datacontent': nilai,
                    '_berkas_raw': str(berkas_relatif),
                    '_sha256_raw': nilai_sha256
                })
        else:
            baris_baru = item.copy() if isinstance(item, dict) else {'raw_content': item}
            baris_baru['jenis_periode'] = jenis_periode
            baris_baru['_berkas_raw'] = str(berkas_relatif)
            baris_baru['_sha256_raw'] = nilai_sha256
            baris_tabel.append(baris_baru)
            
    df = pd.DataFrame(baris_tabel)
    return df

if __name__ == "__main__":
    try:
        file_csv = "bps/2026-10-17/sdg8_tpt.csv"
        df_csv = baca_bps_csv(file_csv)
        print(f"Berhasil membaca CSV! Jumlah baris: {len(df_csv)}")

        file_json = "bps/2026-10-17/json/sdg8_tpt.json"
        df_json = baca_bps_json(file_json)
        print(f"Berhasil membaca JSON! Jumlah baris: {len(df_json)}")
        print(df_json[['_berkas_raw', '_sha256_raw']].head(2))
        
    except Exception as e:
        print(f"Terjadi kesalahan saat membaca berkas: {e}")