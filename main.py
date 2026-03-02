"""
=============================================================
  MBG FOOD POISONING RISK SCORING SYSTEM
  Program Makan Bergizi Gratis - Sistem Penilaian Risiko Keracunan
=============================================================
"""

from loader import DataLoader
from risk_calculator import RiskCalculator
from analyzer import Analyzer
from report import ReportGenerator


class App:
    def __init__(self):
        self.data = None

    def load_data(self):
        path = input("\nMasukkan path file (.xlsx / .csv) [Enter = default]: ").strip()
        if path == "":
            path = "DATA_KERACUNAN_MBG_TERVERIFIKASI.csv"

        loader = DataLoader(path)
        self.data = loader.load()

        if self.data is not None:
            print(f"✅ Data berhasil dimuat: {len(self.data)} baris")

    def hitung_risiko(self):
        if self.data is None:
            print("⚠️  Load data terlebih dahulu!")
            return

        calculator = RiskCalculator()
        self.data = calculator.calculate_all(self.data)
        print("✅ Risk score berhasil dihitung")
        print("\nPreview 5 baris pertama (kolom risiko):")
        cols = ['Provinsi', 'Jumlah Korban', 'Skor Risiko', 'Kategori Risiko', 'Level Risiko']
        print(self.data[[c for c in cols if c in self.data.columns]].head())

    def analisis(self):
        if self.data is None:
            print("⚠️  Load data terlebih dahulu!")
            return
        if 'Skor Risiko' not in self.data.columns:
            print("⚠️  Hitung risk score terlebih dahulu (Menu 2)!")
            return

        analyzer = Analyzer(self.data)
        analyzer.print_full_analysis()

    def generate_report(self):
        if self.data is None:
            print("⚠️  Load data terlebih dahulu!")
            return
        if 'Skor Risiko' not in self.data.columns:
            print("⚠️  Hitung risk score terlebih dahulu (Menu 2)!")
            return

        report = ReportGenerator(self.data)
        report.show_summary()
        report.save_to_csv("hasil_report_mbg.csv")
        report.save_risk_detail("detail_risiko_mbg.csv")

    def run(self):
        print("\n" + "="*55)
        print("  SISTEM RISK SCORING - PROGRAM MAKAN BERGIZI GRATIS")
        print("="*55)

        while True:
            print("\n╔════════════════════════════╗")
            print("║         MENU UTAMA         ║")
            print("╠════════════════════════════╣")
            print("║  1. Load Data              ║")
            print("║  2. Hitung Risk Score      ║")
            print("║  3. Analisis Data          ║")
            print("║  4. Generate Report        ║")
            print("║  5. Exit                   ║")
            print("╚════════════════════════════╝")

            pilih = input("Pilih menu: ").strip()

            if pilih == "1":
                self.load_data()
            elif pilih == "2":
                self.hitung_risiko()
            elif pilih == "3":
                self.analisis()
            elif pilih == "4":
                self.generate_report()
            elif pilih == "5":
                print("\nTerima kasih telah menggunakan sistem ini.\n")
                break
            else:
                print("❌ Pilihan tidak valid. Masukkan angka 1–5.")


if __name__ == "__main__":
    app = App()
    app.run()
