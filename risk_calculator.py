"""
risk_calculator.py — Sistem penilaian risiko multi-faktor untuk MBG
=====================================================================

METODOLOGI RISK SCORING (Total Maks: 100 poin)
───────────────────────────────────────────────
Dimensi 1 – Skala Korban        (0–35 poin)
Dimensi 2 – Jenis Patogen       (0–25 poin)
Dimensi 3 – KLB & Dampak Resmi (0–20 poin)
Dimensi 4 – Rekurensi Lokasi    (0–10 poin)
Dimensi 5 – Kelengkapan Data    (0–10 poin, dihitung invers = penalti data kosong)

KLASIFIKASI RISIKO
──────────────────
  KRITIS   : Skor ≥ 75   → Tindakan darurat segera
  TINGGI   : Skor 50–74  → Intervensi prioritas
  SEDANG   : Skor 25–49  → Pemantauan intensif
  RENDAH   : Skor  0–24  → Pemantauan rutin
"""

import pandas as pd


# ── Tabel patogen/penyebab dan bobot bahayanya ──────────────────────────────
PATOGEN_SCORE = {
    # Patogen spesifik berbahaya tinggi
    'salmonella':         25,
    'e.coli':             22,
    'e-coli':             22,
    'ecoli':              22,
    'staphylococcus':     20,
    'listeria':           25,
    'clostridium':        23,
    # Bakteri generik
    'bakteri':            15,
    'kontaminasi bakteri': 15,
    # Masalah teknis dan higienitas
    'tidak matang':       12,
    'ayam tidak matang':  14,
    'cold chain':         18,   # risiko suhu distribusi tinggi
    'penyimpanan':        16,
    'basi':               14,
    'higienitas rendah':  12,
    'tidak higienis':     12,
    'makanan tidak layak':10,
    # Dugaan / belum konfirmasi
    'dugaan':              8,
    'dalam investigasi':   8,
    'dalam pemantauan':    6,
    # Default
    'kontaminasi makanan': 10,
}


class RiskCalculator:

    def __init__(self):
        self._lokasi_frekuensi = {}  # akan diisi dari data keseluruhan

    # ─────────────────────────────────────────────────
    # DIMENSI 1: Skala Korban (0–35 poin)
    # ─────────────────────────────────────────────────
    def _skor_korban(self, jumlah: int) -> int:
        if jumlah == 0:
            return 5   # data tidak lengkap, beri skor minimal
        elif jumlah >= 500:
            return 35
        elif jumlah >= 300:
            return 30
        elif jumlah >= 100:
            return 25
        elif jumlah >= 50:
            return 18
        elif jumlah >= 20:
            return 12
        elif jumlah >= 10:
            return 7
        else:
            return 3

    # ─────────────────────────────────────────────────
    # DIMENSI 2: Jenis Patogen / Penyebab (0–25 poin)
    # ─────────────────────────────────────────────────
    def _skor_patogen(self, keterangan: str) -> int:
        if not isinstance(keterangan, str):
            return 5
        keterangan_lower = keterangan.lower()
        maks = 0
        for kata_kunci, skor in PATOGEN_SCORE.items():
            if kata_kunci in keterangan_lower:
                maks = max(maks, skor)
        # Bonus jika multi-patogen (lebih dari 1 bakteri teridentifikasi)
        multi = sum(1 for k in ['salmonella', 'e.coli', 'e-coli', 'staphylococcus']
                    if k in keterangan_lower)
        if multi >= 2:
            maks = min(25, maks + 5)
        return maks if maks > 0 else 5

    # ─────────────────────────────────────────────────
    # DIMENSI 3: KLB & Program Dihentikan (0–20 poin)
    # ─────────────────────────────────────────────────
    def _skor_dampak_resmi(self, row) -> int:
        skor = 0
        ket = str(row.get('Penyebab / Keterangan', '')).lower()
        skor_klb = row.get('Flag_KLB', False)
        skor_stop = row.get('Flag_Disetop', False)

        if skor_klb:
            skor += 15   # KLB = status darurat resmi
        if skor_stop:
            skor += 8    # program disetop = dampak serius
        if 'dirawat' in ket or 'rs' in ket or 'rumah sakit' in ket or 'puskesmas' in ket:
            skor += 5    # ada korban dirawat
        return min(skor, 20)

    # ─────────────────────────────────────────────────
    # DIMENSI 4: Rekurensi Lokasi (0–10 poin)
    # ─────────────────────────────────────────────────
    def _skor_rekurensi(self, provinsi: str) -> int:
        frek = self._lokasi_frekuensi.get(str(provinsi).strip().title(), 0)
        if frek >= 10:
            return 10
        elif frek >= 5:
            return 7
        elif frek >= 3:
            return 5
        elif frek >= 2:
            return 3
        return 0

    # ─────────────────────────────────────────────────
    # DIMENSI 5: Penalti Data Tidak Lengkap (0–10 poin)
    #   Skor tinggi = data lengkap (lebih dipercaya)
    #   Skor rendah = data kosong / tidak valid
    # ─────────────────────────────────────────────────
    def _skor_kelengkapan(self, row) -> int:
        skor = 10
        ket = str(row.get('Penyebab / Keterangan', ''))
        tanggal = str(row.get('Tanggal', ''))

        if row.get('Jumlah Korban', 0) == 0:
            skor -= 4  # korban tidak tercatat
        if 'data belum lengkap' in ket.lower():
            skor -= 4
        if tanggal.strip() in ['-', '', 'nan', 'NaT']:
            skor -= 2
        return max(skor, 0)

    # ─────────────────────────────────────────────────
    # HITUNG SKOR TOTAL + KLASIFIKASI
    # ─────────────────────────────────────────────────
    def _hitung_skor_row(self, row) -> dict:
        d1 = self._skor_korban(int(row.get('Jumlah Korban', 0)))
        d2 = self._skor_patogen(row.get('Penyebab / Keterangan', ''))
        d3 = self._skor_dampak_resmi(row)
        d4 = self._skor_rekurensi(row.get('Provinsi', ''))
        d5 = self._skor_kelengkapan(row)
        total = d1 + d2 + d3 + d4 + d5

        # Klasifikasi
        if total >= 75:
            kategori = 'Kritis'
            level = '🔴'
            rekomendasi = 'Tindakan darurat segera, investigasi BPOM/BGN'
        elif total >= 50:
            kategori = 'Tinggi'
            level = '🟠'
            rekomendasi = 'Intervensi prioritas, audit SPPG'
        elif total >= 25:
            kategori = 'Sedang'
            level = '🟡'
            rekomendasi = 'Pemantauan intensif, peningkatan SOP hygiene'
        else:
            kategori = 'Rendah'
            level = '🟢'
            rekomendasi = 'Pemantauan rutin'

        return {
            'Skor_D1_Korban': d1,
            'Skor_D2_Patogen': d2,
            'Skor_D3_KLB': d3,
            'Skor_D4_Rekurensi': d4,
            'Skor_D5_DataLengkap': d5,
            'Skor Risiko': total,
            'Kategori Risiko': kategori,
            'Level Risiko': level,
            'Rekomendasi': rekomendasi,
        }

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        # Hapus kolom hasil scoring lama agar tidak duplikat
        SCORE_COLS = [
            'Skor_D1_Korban', 'Skor_D2_Patogen', 'Skor_D3_KLB',
            'Skor_D4_Rekurensi', 'Skor_D5_DataLengkap',
            'Skor Risiko', 'Kategori Risiko', 'Level Risiko',
            'Rekomendasi', 'Kategori Penyebab', 'Flag_KLB', 'Flag_Disetop'
        ]
        df = df.drop(columns=[c for c in SCORE_COLS if c in df.columns])

        # Reset index agar tidak ada duplikat index
        df = df.reset_index(drop=True)

        # Hitung frekuensi kemunculan tiap provinsi (untuk rekurensi)
        self._lokasi_frekuensi = df['Provinsi'].astype(str).str.strip().str.title().value_counts().to_dict()

        # Tambah flag KLB dan Disetop
        ket_col = df['Penyebab / Keterangan'].astype(str) if 'Penyebab / Keterangan' in df.columns else pd.Series([''] * len(df))
        df['Flag_KLB'] = ket_col.str.contains(r'KLB|luar biasa', case=False, na=False)
        df['Flag_Disetop'] = ket_col.str.contains(r'disetop|dihentikan|ditutup', case=False, na=False)

        # Terapkan scoring ke setiap baris
        hasil = df.apply(self._hitung_skor_row, axis=1, result_type='expand')
        hasil = hasil.reset_index(drop=True)
        df = pd.concat([df, hasil], axis=1)

        # Pastikan tidak ada kolom duplikat
        df = df.loc[:, ~df.columns.duplicated()]

        # Tambah Kategori Penyebab (label ringkas)
        df['Kategori Penyebab'] = df['Penyebab / Keterangan'].apply(self._kategorikan_penyebab)

        return df

    @staticmethod
    def _kategorikan_penyebab(keterangan: str) -> str:
        if not isinstance(keterangan, str):
            return 'Tidak Diketahui'
        k = keterangan.lower()
        if any(p in k for p in ['salmonella', 'e.coli', 'e-coli', 'staphylococcus', 'listeria']):
            return 'Patogen Spesifik'
        elif 'cold chain' in k or 'penyimpanan' in k:
            return 'Rantai Dingin / Penyimpanan'
        elif 'tidak matang' in k or 'ayam' in k:
            return 'Teknis Pemasakan'
        elif 'higienitas' in k or 'tidak higienis' in k or 'basi' in k:
            return 'Higienitas Rendah'
        elif 'bakteri' in k or 'kontaminasi bakteri' in k:
            return 'Kontaminasi Bakteri'
        elif 'dugaan' in k or 'dalam investigasi' in k:
            return 'Dugaan / Belum Terverifikasi'
        else:
            return 'Kontaminasi Makanan Umum'