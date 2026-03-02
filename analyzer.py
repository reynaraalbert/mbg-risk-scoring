"""
analyzer.py — Modul analisis statistik dan insight untuk data MBG
"""

import pandas as pd


class Analyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def total_data(self) -> int:
        return len(self.df)

    def total_korban(self) -> int:
        return int(self.df['Jumlah Korban'].sum())

    def high_risk_count(self) -> int:
        return len(self.df[self.df['Kategori Risiko'].isin(['Tinggi', 'Kritis'])])

    def kritis_count(self) -> int:
        return len(self.df[self.df['Kategori Risiko'] == 'Kritis'])

    def top_penyebab(self, n=5) -> pd.Series:
        return self.df['Kategori Penyebab'].value_counts().head(n)

    def top_provinsi(self, n=10) -> pd.DataFrame:
        return (self.df.groupby('Provinsi')
                .agg(Total_Korban=('Jumlah Korban', 'sum'),
                     Jumlah_Insiden=('Jumlah Korban', 'count'),
                     Rata_Skor=('Skor Risiko', 'mean'))
                .sort_values('Total_Korban', ascending=False)
                .head(n)
                .round(1))

    def distribusi_risiko(self) -> pd.Series:
        urutan = ['Kritis', 'Tinggi', 'Sedang', 'Rendah']
        hasil = self.df['Kategori Risiko'].value_counts()
        return hasil.reindex(urutan, fill_value=0)

    def tren_bulanan(self) -> pd.DataFrame:
        if 'Bulan_Num' not in self.df.columns:
            return pd.DataFrame()
        bulan_nama = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'Mei',6:'Jun',
                      7:'Jul',8:'Agu',9:'Sep',10:'Okt',11:'Nov',12:'Des'}
        tren = (self.df.groupby(['Tahun', 'Bulan_Num'])
                .agg(Insiden=('Jumlah Korban','count'),
                     Korban=('Jumlah Korban','sum'))
                .reset_index())
        tren['Bulan'] = tren['Bulan_Num'].map(bulan_nama)
        return tren

    def kasus_klb(self) -> pd.DataFrame:
        if 'Flag_KLB' not in self.df.columns:
            return pd.DataFrame()
        return self.df[self.df['Flag_KLB'] == True][
            ['Tanggal', 'Provinsi', 'Kabupaten/Kota', 'Jumlah Korban',
             'Kategori Risiko', 'Skor Risiko']
        ].sort_values('Skor Risiko', ascending=False)

    def print_full_analysis(self):
        df = self.df
        sep = "─" * 55

        print(f"\n{'='*55}")
        print("   ANALISIS RISIKO KERACUNAN MBG")
        print(f"{'='*55}")

        # Ringkasan Umum
        print(f"\n{sep}")
        print("  📊 RINGKASAN UMUM")
        print(sep)
        print(f"  Total insiden tercatat  : {self.total_data()}")
        print(f"  Total korban            : {self.total_korban():,}")
        print(f"  Kasus KRITIS            : {self.kritis_count()}")
        print(f"  Kasus Risiko Tinggi+    : {self.high_risk_count()}")
        print(f"  Rata-rata skor risiko   : {df['Skor Risiko'].mean():.1f}")
        print(f"  Skor risiko tertinggi   : {df['Skor Risiko'].max()}")

        # Distribusi Risiko
        print(f"\n{sep}")
        print("  🎯 DISTRIBUSI LEVEL RISIKO")
        print(sep)
        dist = self.distribusi_risiko()
        ikon = {'Kritis': '🔴', 'Tinggi': '🟠', 'Sedang': '🟡', 'Rendah': '🟢'}
        for level, jml in dist.items():
            pct = jml / len(df) * 100 if len(df) > 0 else 0
            print(f"  {ikon.get(level,'⚪')} {level:<10}: {jml:>4} kasus ({pct:.1f}%)")

        # Top Provinsi
        print(f"\n{sep}")
        print("  📍 TOP 10 PROVINSI (Berdasarkan Jumlah Korban)")
        print(sep)
        print(f"  {'Provinsi':<30} {'Korban':>8} {'Insiden':>8} {'Skor Rata²':>10}")
        print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*10}")
        for prov, row in self.top_provinsi(10).iterrows():
            print(f"  {prov:<30} {int(row.Total_Korban):>8,} {int(row.Jumlah_Insiden):>8} {row.Rata_Skor:>10.1f}")

        # Top Penyebab
        print(f"\n{sep}")
        print("  🦠 TOP KATEGORI PENYEBAB")
        print(sep)
        for penyebab, jml in self.top_penyebab().items():
            pct = jml / len(df) * 100
            print(f"  • {penyebab:<35}: {jml:>3} ({pct:.1f}%)")

        # Kasus KLB
        klb = self.kasus_klb()
        if not klb.empty:
            print(f"\n{sep}")
            print(f"  🚨 KEJADIAN LUAR BIASA (KLB): {len(klb)} kasus")
            print(sep)
            for _, r in klb.iterrows():
                print(f"  [{r['Kategori Risiko']}] {r.get('Tanggal','-')} | "
                      f"{r['Provinsi']} - {r.get('Kabupaten/Kota','')} | "
                      f"{int(r['Jumlah Korban'])} korban | Skor: {r['Skor Risiko']}")

        # Tren Bulanan
        tren = self.tren_bulanan()
        if not tren.empty:
            print(f"\n{sep}")
            print("  📅 TREN BULANAN 2025–2026")
            print(sep)
            print(f"  {'Periode':<12} {'Insiden':>8} {'Korban':>8}")
            print(f"  {'-'*12} {'-'*8} {'-'*8}")
            for _, r in tren.sort_values(['Tahun','Bulan_Num']).iterrows():
                if r['Bulan_Num'] > 0:
                    print(f"  {r['Bulan']}-{int(r['Tahun']):<7} {int(r['Insiden']):>8} {int(r['Korban']):>8,}")

        # 5 Kasus Terberisiko
        print(f"\n{sep}")
        print("  ⚠️  5 KASUS DENGAN SKOR RISIKO TERTINGGI")
        print(sep)
        top5 = df.nlargest(5, 'Skor Risiko')[
            ['Tanggal', 'Provinsi', 'Kabupaten/Kota',
             'Jumlah Korban', 'Kategori Risiko', 'Skor Risiko', 'Rekomendasi']
        ]
        for i, (_, r) in enumerate(top5.iterrows(), 1):
            print(f"\n  [{i}] {r['Level Risiko'] if 'Level Risiko' in r else ''} "
                  f"{r['Provinsi']} – {r.get('Kabupaten/Kota','')}")
            print(f"      Tanggal  : {r.get('Tanggal', '-')}")
            print(f"      Korban   : {int(r['Jumlah Korban'])}")
            print(f"      Risiko   : {r['Kategori Risiko']}  (Skor: {r['Skor Risiko']})")
            print(f"      Aksi     : {r['Rekomendasi']}")

        print(f"\n{'='*55}\n")
