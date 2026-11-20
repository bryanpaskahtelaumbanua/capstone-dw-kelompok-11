import json
import tempfile
from pathlib import Path
import pandas as pd

# Sesuaikan import dengan nama file/modul pembaca Anda, misalnya:
# from pembaca_bps import baca_bps_csv, baca_bps_json
# atau:
# from src.ingest.pembaca_bps import baca_bps_csv, baca_bps_json


def ambil_berkas_bps_dari_manifest(data_manifest: dict) -> list[str]:
    """Ambil daftar path relatif berkas BPS dari manifest."""
    daftar = []
    for item in data_manifest.get("files", []):
        if isinstance(item, dict):
            path = item.get("path") or item.get("berkas")
            sumber = str(item.get("source", "")).lower()
            if path and ("bps" in sumber or str(path).startswith("bps/")):
                daftar.append(str(path))
    return list(dict.fromkeys(daftar))


def uji_periode_dan_manifest():
    # Gunakan direktori sementara agar file asli proyek tidak terganggu
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_tmp = Path(tmp_dir)
        raw_dir = base_tmp / "data" / "raw"
        (raw_dir / "bps" / "2026-10-17" / "json").mkdir(parents=True, exist_ok=True)

        rel_csv = "bps/2026-10-17/sdg8_tpt.csv"
        rel_json = "bps/2026-10-17/json/sdg8_tpt.json"

        # 1. Buat data uji CSV dan JSON dengan periode Februari, Agustus, Tahunan
        (raw_dir / rel_csv).write_text(
            "vervar,tahun,jenis_periode,nilai\n"
            "1800,2025,Februari,4.12\n"
            "1800,2025,Agustus,4.35\n"
            "1800,2025,Tahunan,4.24\n",
            encoding="utf-8",
        )

        payload_json = [
            {"vervar": "1800", "turtahun": "Februari", "datacontent": {"2025": 4.12}},
            {"vervar": "1800", "turtahun": "Agustus", "datacontent": {"2025": 4.35}},
            {"vervar": "1800", "turtahun": "Tahunan", "datacontent": {"2025": 4.24}},
        ]
        (raw_dir / rel_json).write_text(json.dumps(payload_json), encoding="utf-8")

        # 2. Simulasi manifest berisi berkas BPS & non-BPS
        manifest_dummy = {
            "files": [
                {"path": rel_csv, "source": "bps"},
                {"path": rel_json, "source": "bps"},
                {"path": "non_bps/2026-10-17/lain.csv", "source": "lain"},
            ]
        }

        # Ganti sementara DATA_RAW dan sha256_raw di modul pembaca Anda
        import pembaca_bps as mod  # ganti sesuai nama modul Anda

        mod.DATA_RAW = raw_dir
        mod.sha256_raw = lambda rel: f"dummy_sha256_{rel}"

        # 3. Uji pemetaan periode pada CSV dan JSON
        df_csv = mod.baca_bps_csv(rel_csv)
        df_json = mod.baca_bps_json(rel_json)

        periode_diharapkan = {"Februari", "Agustus", "Tahunan"}
        periode_csv = set(df_csv["jenis_periode"].dropna().unique())
        periode_json = set(df_json["jenis_periode"].dropna().unique())

        assert periode_diharapkan.issubset(periode_csv), f"CSV kurang periode: {periode_csv}"
        assert periode_diharapkan.issubset(periode_json), f"JSON kurang periode: {periode_json}"
        print("[OK] Pemetaan Februari, Agustus, dan Tahunan valid pada CSV & JSON.")

        # 4. Uji seluruh berkas BPS di manifest terproses
        berkas_bps = ambil_berkas_bps_dari_manifest(manifest_dummy)
        assert len(berkas_bps) == 2

        kumpulan_df = []
        for berkas in berkas_bps:
            if berkas.endswith(".csv"):
                kumpulan_df.append(mod.baca_bps_csv(berkas))
            elif berkas.endswith(".json"):
                kumpulan_df.append(mod.baca_bps_json(berkas))

        df_all = pd.concat(kumpulan_df, ignore_index=True)
        terproses = set(df_all["_berkas_raw"].unique())

        assert terproses == set(berkas_bps), (
            f"Berkas belum terproses: {set(berkas_bps) - terproses}"
        )
        assert df_all["_sha256_raw"].notna().all()
        print(f"[OK] Seluruh {len(berkas_bps)} berkas BPS dalam manifest berhasil diproses.")


if __name__ == "__main__":
    uji_periode_dan_manifest()