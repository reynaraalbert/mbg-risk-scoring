"""
report.py — ReportGenerator: menyimpan hasil analisis ke CSV
"""

import pandas as pd


class ReportGenerator:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def show_summary(self):
        print("\n=== RINGKASAN LAPORAN ===")
        print(f"Total insiden : {len(self.df)}")
        print(f"Total korban  : {self.df['Jumlah Korban'].sum():,}")

        print("\nDistribusi Risiko:")
        urutan = ['Kritis', 'Tinggi', 'Sedang', 'Rendah']
        dist = self.df['Kategori Risiko'].value_counts().reindex(urutan, fill_value=0)
        for k, v in dist.items():
            print(f"  {k:<10}: {v}")

    def save_to_csv(self, filename: str = "hasil_report_mbg.csv"):
        """Simpan seluruh data + kolom risiko ke CSV."""
        try:
            self.df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"✅ Report lengkap disimpan: {filename}")
        except Exception as e:
            print(f"❌ Gagal menyimpan: {e}")

    def save_risk_detail(self, filename: str = "detail_risiko_mbg.csv"):
        """Simpan hanya kolom ringkasan risiko per insiden."""
        cols = [
            'No', 'Tahun', 'Bulan', 'Tanggal', 'Provinsi', 'Kabupaten/Kota',
            'Jumlah Korban', 'Kategori Penyebab', 'Kategori Risiko', 'Level Risiko',
            'Skor Risiko', 'Skor_D1_Korban', 'Skor_D2_Patogen', 'Skor_D3_KLB',
            'Skor_D4_Rekurensi', 'Skor_D5_DataLengkap', 'Flag_KLB', 'Flag_Disetop',
            'Rekomendasi'
        ]
        export_cols = [c for c in cols if c in self.df.columns]
        try:
            self.df[export_cols].sort_values('Skor Risiko', ascending=False).to_csv(
                filename, index=False, encoding='utf-8-sig'
            )
            print(f"✅ Detail risiko disimpan: {filename}")
        except Exception as e:
            print(f"❌ Gagal menyimpan detail: {e}")
