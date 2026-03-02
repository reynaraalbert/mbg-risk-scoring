"""
loader.py - DataLoader: membaca dan membersihkan data MBG
Versi upgrade: auto-detect kolom, support semua format Excel, multi-sheet, fallback cerdas
"""

import pandas as pd
import io


class DataLoader:
    COLUMN_ALIASES = {
        'Jumlah Korban': [
            'jumlah korban', 'korban', 'total korban', 'jml korban',
            'jumlah_korban', 'victims', 'total victims', 'jumlah siswa sakit',
            'siswa sakit', 'jumlah sakit', 'sakit', 'penderita',
            'jumlah penderita', 'jumlah orang sakit', 'orang sakit',
        ],
        'Penyebab / Keterangan': [
            'penyebab / keterangan', 'penyebab', 'keterangan', 'cause',
            'description', 'deskripsi', 'penyebab/keterangan', 'penyebab keterangan',
            'ket', 'keterangan kejadian', 'dugaan penyebab', 'penyebab dugaan',
            'patogen', 'informasi', 'info', 'notes', 'catatan', 'kasus',
            'detail', 'detail kejadian', 'uraian', 'uraian kejadian',
            'kronologi', 'kejadian', 'insiden', 'keterangan insiden',
            'penyebab keracunan', 'penyebab insiden', 'jenis penyebab',
        ],
        'Provinsi': [
            'provinsi', 'province', 'propinsi', 'prov', 'wilayah provinsi',
            'nama provinsi', 'lokasi provinsi',
        ],
        'Kabupaten/Kota': [
            'kabupaten/kota', 'kabupaten kota', 'kab/kota', 'kota', 'kabupaten',
            'city', 'district', 'kab', 'regency', 'daerah', 'wilayah',
            'nama kota', 'nama kabupaten',
        ],
        'Tanggal': [
            'tanggal', 'date', 'tgl', 'tanggal kejadian', 'waktu kejadian',
            'tanggal insiden', 'tgl kejadian',
        ],
        'Bulan': [
            'bulan', 'month', 'bln',
        ],
        'Tahun': [
            'tahun', 'year', 'thn',
        ],
        'No': [
            'no', 'no.', 'nomor', 'number', 'no urut', 'no_urut', 'id',
        ],
    }

    REQUIRED_COLUMNS = ['Jumlah Korban', 'Penyebab / Keterangan', 'Provinsi']

    def __init__(self, path=None, sheet_name=0):
        self.path = path
        self.sheet_name = sheet_name
        self.column_mapping = {}
        self.warnings = []

    @staticmethod
    def get_sheet_names(path_or_bytes) -> list:
        try:
            xls = pd.ExcelFile(path_or_bytes)
            return xls.sheet_names
        except Exception:
            return []

    def load(self):
        try:
            df = self._read_file()
            if df is None:
                return None
            df = self._detect_header_row(df)
            df = self._normalize_column_names(df)
            df = self._map_columns(df)
            missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                for col in missing:
                    df[col] = None
                    self.warnings.append(f"Kolom '{col}' tidak ditemukan - diisi nilai kosong.")
            df = self._clean(df)
            return df
        except Exception as e:
            import traceback
            print(f"Error: {e}")
            traceback.print_exc()
            return None

    def _read_file(self):
        path = str(self.path).lower()
        if path.endswith(('.xlsx', '.xls', '.xlsm')):
            try:
                return pd.read_excel(self.path, sheet_name=self.sheet_name, header=0)
            except Exception:
                return pd.read_excel(self.path, sheet_name=0, header=0)
        elif path.endswith('.csv'):
            for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
                try:
                    return pd.read_csv(self.path, encoding=enc)
                except UnicodeDecodeError:
                    continue
        return None

    def _detect_header_row(self, df):
        all_aliases = set()
        for aliases in self.COLUMN_ALIASES.values():
            all_aliases.update(aliases)
        best_row = -1
        best_score = 0
        for i in range(min(10, len(df))):
            row_vals = [str(v).strip().lower() for v in df.iloc[i].values if pd.notna(v)]
            score = sum(1 for v in row_vals if v in all_aliases)
            if score > best_score:
                best_score = score
                best_row = i
        if best_score >= 2 and best_row > 0:
            df.columns = df.iloc[best_row].astype(str).str.strip()
            df = df.iloc[best_row + 1:].reset_index(drop=True)
            self.warnings.append(f"Header terdeteksi di baris ke-{best_row + 1}.")
        return df

    def _normalize_column_names(self, df):
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.replace(r'\s+', ' ', regex=True)
            .str.replace('\n', ' ')
        )
        return df

    def _map_columns(self, df):
        rename_map = {}
        for std_name, aliases in self.COLUMN_ALIASES.items():
            if std_name in df.columns:
                continue
            for col in df.columns:
                if col.lower().strip() in aliases:
                    rename_map[col] = std_name
                    self.column_mapping[col] = std_name
                    break
        if rename_map:
            df = df.rename(columns=rename_map)
        df = self._fallback_detect(df)
        return df

    def _fallback_detect(self, df):
        used_cols = set(self.COLUMN_ALIASES.keys())
        remaining_cols = [c for c in df.columns if c not in used_cols]

        # Fallback Jumlah Korban: kolom numerik nilai 1-10000
        if 'Jumlah Korban' not in df.columns:
            for col in remaining_cols:
                try:
                    nums = pd.to_numeric(df[col], errors='coerce').dropna()
                    if len(nums) > len(df) * 0.5 and nums.between(1, 10000).mean() > 0.5:
                        df = df.rename(columns={col: 'Jumlah Korban'})
                        self.column_mapping[col] = 'Jumlah Korban'
                        self.warnings.append(f"Kolom '{col}' dideteksi otomatis sebagai 'Jumlah Korban'")
                        remaining_cols = [c for c in remaining_cols if c != col]
                        break
                except Exception:
                    pass

        # Fallback Provinsi: isi mirip nama provinsi Indonesia
        if 'Provinsi' not in df.columns:
            provinsi_indo = {
                'jawa', 'sumatera', 'kalimantan', 'sulawesi', 'bali', 'papua',
                'jakarta', 'aceh', 'riau', 'jambi', 'lampung', 'bengkulu',
                'yogyakarta', 'ntb', 'ntt', 'maluku', 'gorontalo',
            }
            for col in remaining_cols:
                try:
                    vals = df[col].astype(str).str.lower()
                    match = vals.apply(lambda v: any(p in v for p in provinsi_indo)).sum()
                    if match > len(df) * 0.2:
                        df = df.rename(columns={col: 'Provinsi'})
                        self.column_mapping[col] = 'Provinsi'
                        self.warnings.append(f"Kolom '{col}' dideteksi otomatis sebagai 'Provinsi'")
                        remaining_cols = [c for c in remaining_cols if c != col]
                        break
                except Exception:
                    pass

        # Fallback Penyebab/Keterangan: kolom teks paling panjang rata-ratanya
        if 'Penyebab / Keterangan' not in df.columns:
            best_col = None
            best_len = 0
            for col in remaining_cols:
                try:
                    avg_len = df[col].astype(str).str.len().mean()
                    if avg_len > best_len and avg_len > 10:
                        best_len = avg_len
                        best_col = col
                except Exception:
                    pass
            if best_col:
                df = df.rename(columns={best_col: 'Penyebab / Keterangan'})
                self.column_mapping[best_col] = 'Penyebab / Keterangan'
                self.warnings.append(f"Kolom '{best_col}' dideteksi otomatis sebagai 'Penyebab / Keterangan'")

        return df

    def _clean(self, df):
        df = df.dropna(how='all').reset_index(drop=True)

        if 'Jumlah Korban' in df.columns:
            df['Jumlah Korban'] = (
                df['Jumlah Korban']
                .astype(str)
                .str.extract(r'(\d+)')[0]
                .pipe(pd.to_numeric, errors='coerce')
                .fillna(0)
                .astype(int)
            )

        bulan_map = {
            'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
            'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
            'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
            'january': 1, 'february': 2, 'march': 3, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'october': 10, 'december': 12,
        }
        if 'Bulan' in df.columns:
            df['Bulan_Num'] = (
                df['Bulan'].astype(str).str.strip().str.lower()
                .map(bulan_map)
                .fillna(0)
                .astype(int)
            )

        if 'Provinsi' in df.columns:
            df['Provinsi'] = df['Provinsi'].astype(str).str.strip().str.title()
            df = df[~df['Provinsi'].isin(['Nan', 'None', '', '-'])].reset_index(drop=True)

        if 'Penyebab / Keterangan' in df.columns:
            ket = df['Penyebab / Keterangan'].astype(str)
            df['Flag_KLB'] = ket.str.contains(r'KLB|luar biasa', case=False, na=False)
            df['Flag_Disetop'] = ket.str.contains(
                r'disetop|dihentikan|ditutup|berhenti', case=False, na=False
            )
        else:
            df['Flag_KLB'] = False
            df['Flag_Disetop'] = False

        return df