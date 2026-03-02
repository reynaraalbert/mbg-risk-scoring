"""
app.py — Streamlit Dashboard: MBG Food Poisoning Risk Scoring System
Jalankan dengan: streamlit run app.py
"""

import io
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from loader import DataLoader
from risk_calculator import RiskCalculator
from analyzer import Analyzer

DEFAULT_CSV = "DATA_KERACUNAN_MBG_TERVERIFIKASI.csv"

import base64, pathlib

def get_logo_base64(path="logo_bgn.png"):
    try:
        img_bytes = pathlib.Path(path).read_bytes()
        return base64.b64encode(img_bytes).decode()
    except Exception:
        return None

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MBG Risk Scoring",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded"
)

BG_CARD      = "#ffffff"
BLUE_PRIMARY = "#4a90d9"
BLUE_DARK    = "#2c6fad"
BLUE_LIGHT   = "#cce3f8"
BLUE_ACCENT  = "#7bb8f0"
TEXT_MAIN    = "#1a2f4a"
TEXT_MUTED   = "#6b8caa"
BORDER       = "#b8d6f0"
CHART_BG     = "rgba(240,246,255,0)"
GRID_COLOR   = "#d0e8f8"
FONT_COLOR   = "#1a2f4a"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Nunito', sans-serif; }
    .stApp { background: linear-gradient(160deg, #e8f4ff 0%, #f5faff 50%, #edf6ff 100%); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #d6ecff 0%, #e8f4ff 100%) !important;
        border-right: 1px solid #b8d6f0;
    }
    [data-testid="stSidebarContent"] { background: transparent !important; }
    .page-header {
        background: linear-gradient(135deg, #4a90d9 0%, #2c6fad 60%, #1a5499 100%);
        border-radius: 16px; padding: 28px 36px; margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(74,144,217,0.25);
    }
    .page-header h1 { color: #ffffff !important; font-size: clamp(20px, 3vw, 30px); font-weight: 900; margin: 0 0 6px 0; }
    .page-header p { color: #c8e0f7; font-size: 14px; margin: 0; }
    .metric-card {
        background: #ffffff; border: 1.5px solid #b8d6f0; border-top: 4px solid #4a90d9;
        border-radius: 14px; padding: 18px 16px 14px; text-align: center;
        box-shadow: 0 2px 12px rgba(74,144,217,0.10);
    }
    .metric-card .label { font-size: 11px; color: #6b8caa; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 700; margin-bottom: 8px; }
    .metric-card .value { font-size: clamp(22px, 3vw, 32px); font-weight: 900; color: #2c6fad; font-family: 'JetBrains Mono', monospace; line-height: 1; }
    .metric-card .sub { font-size: 11px; color: #6b8caa; margin-top: 6px; font-weight: 600; }
    .val-kritis { color: #e03e5a !important; }
    .val-tinggi { color: #e07830 !important; }
    .section-title { font-size: 15px; font-weight: 800; color: #2c6fad; padding: 10px 0 6px; border-bottom: 2px solid #cce3f8; margin-bottom: 12px; }
    .info-box { background: linear-gradient(135deg, #e8f4ff 0%, #d6ecff 100%); border: 1.5px solid #7bb8f0; border-left: 5px solid #4a90d9; border-radius: 10px; padding: 16px 20px; color: #1a2f4a; font-size: 14px; font-weight: 600; }
    .stDownloadButton > button { background: linear-gradient(135deg, #4a90d9, #2c6fad) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 700 !important; padding: 10px 20px !important; width: 100% !important; }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #1a2f4a !important; }
    .footer { text-align: center; padding: 16px; color: #6b8caa; font-size: 12px; font-weight: 600; border-top: 1px solid #b8d6f0; margin-top: 24px; }
</style>
""", unsafe_allow_html=True)


def chart_layout(**kwargs):
    base = dict(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family='Nunito'),
        margin=dict(t=16, b=16, l=8, r=8),
    )
    base.update(kwargs)
    return base



def alert_box(icon, title, body):
    st.markdown(f"""
    <div style='background:#fffbe6;border:1.5px solid #ffe58f;border-left:5px solid #faad14;
    border-radius:12px;padding:18px 22px;margin:10px 0;'>
        <div style='font-size:18px;font-weight:800;color:#7c5c00;margin-bottom:6px;'>{icon} {title}</div>
        <div style='color:#5c4200;font-size:14px;font-weight:600;line-height:1.6;'>{body}</div>
    </div>
    """, unsafe_allow_html=True)

def is_data_sheet(sheet_name, file_bytes):
    """Cek apakah sheet berisi data insiden (bukan ringkasan)."""
    try:
        df_tmp = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=0, nrows=5)
        cols = [str(c).lower() for c in df_tmp.columns]
        keywords = ['provinsi', 'korban', 'penyebab', 'keterangan', 'bulan', 'tahun', 'tanggal', 'kab']
        return sum(1 for k in keywords if any(k in c for c in cols)) >= 2
    except Exception:
        return False


@st.cache_data
def get_sheets(file_bytes, filename):
    return DataLoader.get_sheet_names(io.BytesIO(file_bytes))


@st.cache_data
def load_and_score(file_bytes, filename, sheet_name=0):
    try:
        suffix = os.path.splitext(filename)[1].lower()
        if suffix in ('.xlsx', '.xls', '.xlsm'):
            df_raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=0)
        elif suffix == '.csv':
            df_raw = None
            for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
                try:
                    df_raw = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            if df_raw is None:
                return None, ["❌ Gagal membaca CSV: encoding tidak dikenali"], {}
        else:
            return None, ["❌ Format file tidak didukung"], {}

        loader = DataLoader.__new__(DataLoader)
        loader.path = filename
        loader.sheet_name = sheet_name
        loader.column_mapping = {}
        loader.warnings = []

        df = loader._detect_header_row(df_raw)
        df = loader._normalize_column_names(df)
        df = loader._map_columns(df)

        for col in DataLoader.REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = None
                loader.warnings.append(f"Kolom '{col}' tidak ditemukan — diisi nilai kosong.")

        df = loader._clean(df)
        calc = RiskCalculator()
        df = calc.calculate_all(df)
        return df, loader.warnings, loader.column_mapping

    except Exception as e:
        import traceback
        return None, [f"❌ Error: {e}\n{traceback.format_exc()}"], {}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo BGN di sidebar
    _sidebar_logo = get_logo_base64()
    if _sidebar_logo:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:4px 0 8px 0;">
            <img src="data:image/png;base64,{_sidebar_logo}" 
                style="height:56px;width:56px;object-fit:contain;border-radius:50%;
                box-shadow:0 2px 8px rgba(0,0,0,0.2);flex-shrink:0;" />
            <div>
                <div style="font-size:15px;font-weight:900;color:#1a2f4a;line-height:1.2;">MBG Risk Scoring</div>
                <div style="font-size:11px;font-weight:600;color:#4a90d9;line-height:1.3;">Program Makan Bergizi Gratis</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("## 🍱 MBG Risk Scoring")
        st.markdown("**Program Makan Bergizi Gratis**")
    st.markdown("*Sistem Penilaian Risiko Keracunan*")
    st.divider()

    uploaded = st.file_uploader(
        "📂 Upload Data (.xlsx / .csv)",
        type=['xlsx', 'csv', 'xls', 'xlsm'],
        help="Upload file Excel atau CSV — sistem otomatis mendeteksi kolom"
    )

    selected_sheet = 0
    file_bytes_cache = None

    if uploaded is not None:
        file_bytes_cache = uploaded.read()
        uploaded.seek(0)

        if uploaded.name.lower().endswith(('.xlsx', '.xls', '.xlsm')):
            all_sheets = get_sheets(file_bytes_cache, uploaded.name)
            data_sheets = [s for s in all_sheets if is_data_sheet(s, file_bytes_cache)]
            non_data_sheets = [s for s in all_sheets if s not in data_sheets]

            if len(all_sheets) > 1:
                default_idx = all_sheets.index(data_sheets[0]) if data_sheets else 0
                selected_sheet = st.selectbox(
                    "📋 Pilih Sheet",
                    options=all_sheets,
                    index=default_idx,
                    format_func=lambda s: f"✅ {s}" if s in data_sheets else f"⛔ {s} (bukan data)"
                )
                if selected_sheet in non_data_sheets:
                    st.info(f"ℹ️ Sheet **'{selected_sheet}'** berisi ringkasan, bukan data insiden. Pilih sheet bertanda ✅.")
            elif len(all_sheets) == 1:
                selected_sheet = all_sheets[0]

    st.divider()
    st.markdown("**📊 Metodologi Scoring**")
    st.markdown("""
| Dimensi | Bobot |
|---|---|
| 🧍 Skala Korban | 35 pts |
| 🦠 Jenis Patogen | 25 pts |
| 🚨 KLB & Dampak | 20 pts |
| 🔁 Rekurensi Lokasi | 10 pts |
| 📋 Kelengkapan Data | 10 pts |
    """)
    st.divider()
    st.markdown("**🎯 Klasifikasi**")
    st.markdown("🔴 **Kritis** : ≥ 75")
    st.markdown("🟠 **Tinggi** : 50–74")
    st.markdown("🟡 **Sedang** : 25–49")
    st.markdown("🟢 **Rendah** : < 25")


# ── Header ────────────────────────────────────────────────────────────────────
_logo_b64 = get_logo_base64()
_logo_html = (
    f'<img src="data:image/png;base64,{_logo_b64}" '
    f'style="height:80px;width:80px;object-fit:contain;border-radius:50%;'
    f'box-shadow:0 2px 10px rgba(0,0,0,0.25);flex-shrink:0;" />'
    if _logo_b64 else ""
)

st.markdown(f"""
<div class="page-header" style="display:flex;align-items:center;gap:20px;">
    {_logo_html}
    <div>
        <h1 style="margin:0 0 4px 0;">Dashboard Risiko Keracunan MBG</h1>
        <p style="margin:0;color:#c8e0f7;font-size:13px;font-weight:600;">
            Badan Gizi Nasional Republik Indonesia<br>
            Sistem analisis dan penilaian risiko Program Makan Bergizi Gratis — berbasis data insiden terverifikasi
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

if uploaded is None:
    st.markdown('<div class="info-box">👈 Upload file data di sidebar kiri untuk memulai analisis.</div>', unsafe_allow_html=True)
    st.stop()

# ── Load Data ─────────────────────────────────────────────────────────────────
df, load_warnings, col_mapping = load_and_score(file_bytes_cache, uploaded.name, selected_sheet)

# Validasi sheet
if df is None or len(df) == 0:
    alert_box("📂", "Sheet Kosong",
        "Sheet yang dipilih tidak berisi data atau tidak bisa dibaca.<br>"
        "Silakan pilih sheet lain di <b>sidebar kiri</b>.")
    st.stop()

# Cek sheet valid sebelum lanjut apapun
try:
    if 'Provinsi' in df.columns:
        _prov_col = df['Provinsi']
        if hasattr(_prov_col, 'iloc'):  # pastikan Series bukan DataFrame
            _prov_vals_check = [str(v) for v in _prov_col.dropna().tolist()
                                if str(v).strip() not in ('', 'nan', 'None', '-')]
            prov_valid = len(_prov_vals_check) > 0
        else:
            prov_valid = False
    else:
        prov_valid = False
except Exception:
    prov_valid = False

if not prov_valid:
    all_sheets_check = get_sheets(file_bytes_cache, uploaded.name)
    good_sheets = [s for s in all_sheets_check if is_data_sheet(s, file_bytes_cache)]
    hint = ("Pilih sheet: <b>" + ", ".join(good_sheets) + "</b> di sidebar kiri.") if good_sheets else "Silakan pilih sheet data di sidebar kiri."
    alert_box("📋", "Sheet Bukan Data Utama",
        f"Sheet <b>'{selected_sheet}'</b> berisi ringkasan/statistik, bukan data baris insiden.<br><br>{hint}")
    st.stop()

# Tampilkan info & warning
if col_mapping:
    mapping_text = ", ".join([f"**{k}** → `{v}`" for k, v in col_mapping.items()])
    alert_box('🔄', 'Kolom Otomatis Terdeteksi', mapping_text)

for w in load_warnings:
    alert_box("ℹ️", "Informasi Kolom", w)

analyzer = Analyzer(df)

# ── Filters ───────────────────────────────────────────────────────────────────
with st.expander("🔍 Filter Data", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        try:
            _p = df['Provinsi'] if 'Provinsi' in df.columns else pd.Series([])
            prov_vals = sorted(list(set(
                str(v) for v in _p.dropna().tolist()
                if str(v).strip() not in ('nan', 'None', '', '-')
            )))
        except Exception:
            prov_vals = []
        prov_filter = st.multiselect("Provinsi", prov_vals, default=[])
    with col2:
        level_filter = st.multiselect("Kategori Risiko", ['Kritis', 'Tinggi', 'Sedang', 'Rendah'], default=[])
    with col3:
        if 'Tahun' in df.columns:
            tahun_vals = sorted([str(v) for v in df['Tahun'].dropna().unique()
                                if str(v).strip() not in ('nan', 'None', '')])
            tahun_filter = st.multiselect("Tahun", tahun_vals, default=[])
        else:
            tahun_filter = []

df_filtered = df.copy()
if prov_filter:  df_filtered = df_filtered[df_filtered['Provinsi'].astype(str).isin(prov_filter)]
if level_filter: df_filtered = df_filtered[df_filtered['Kategori Risiko'].isin(level_filter)]
if tahun_filter: df_filtered = df_filtered[df_filtered['Tahun'].astype(str).isin(tahun_filter)]

a = Analyzer(df_filtered)
dist = a.distribusi_risiko()
avg_skor = df_filtered['Skor Risiko'].mean() if len(df_filtered) > 0 else 0

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f'<div class="metric-card"><div class="label">Total Insiden</div><div class="value">{a.total_data()}</div><div class="sub">kejadian tercatat</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="label">Total Korban</div><div class="value">{a.total_korban():,}</div><div class="sub">jiwa terdampak</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="label">🔴 Kasus Kritis</div><div class="value val-kritis">{dist.get("Kritis", 0)}</div><div class="sub">skor ≥ 75</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="label">🟠 Risiko Tinggi</div><div class="value val-tinggi">{dist.get("Tinggi", 0)}</div><div class="sub">skor 50–74</div></div>', unsafe_allow_html=True)
with c5:
    st.markdown(f'<div class="metric-card"><div class="label">Rata-rata Skor</div><div class="value">{avg_skor:.1f}</div><div class="sub">dari 100 poin</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Pie + Bar ─────────────────────────────────────────────────────────────────
col_l, col_r = st.columns([1, 2])
with col_l:
    st.markdown('<div class="section-title">🎯 Distribusi Level Risiko</div>', unsafe_allow_html=True)
    pie_data = dist.reset_index()
    pie_data.columns = ['Level', 'Jumlah']
    fig_pie = px.pie(pie_data, values='Jumlah', names='Level', hole=0.58,
        color='Level', color_discrete_map={'Kritis': '#e03e5a', 'Tinggi': '#e07830', 'Sedang': '#c8970a', 'Rendah': '#1f9e5e'})
    fig_pie.update_layout(**chart_layout(legend=dict(orientation='h', yanchor='bottom', y=-0.25, font=dict(color=FONT_COLOR))))
    fig_pie.update_traces(textinfo='label+percent', textfont=dict(size=12, color=FONT_COLOR),
        marker=dict(line=dict(color='#ffffff', width=2)))
    st.plotly_chart(fig_pie, use_container_width=True)

with col_r:
    st.markdown('<div class="section-title">📍 Top 10 Provinsi Berdasarkan Korban</div>', unsafe_allow_html=True)
    top_prov = a.top_provinsi(10).reset_index()
    fig_bar = px.bar(top_prov, x='Total_Korban', y='Provinsi', orientation='h',
        text='Total_Korban', color='Rata_Skor',
        color_continuous_scale=[[0, '#a8d8f8'], [0.35, BLUE_PRIMARY], [0.65, '#e07830'], [1, '#e03e5a']],
        range_color=[0, 100], labels={'Total_Korban': 'Total Korban', 'Rata_Skor': 'Rata² Skor'})
    fig_bar.update_layout(**chart_layout(
        yaxis=dict(categoryorder='total ascending', gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR)),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR)),
        coloraxis_colorbar=dict(title=dict(text='Skor', font=dict(color=FONT_COLOR)), tickfont=dict(color=FONT_COLOR))
    ))
    fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside', textfont=dict(color=FONT_COLOR, size=11))
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Tren Bulanan ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📅 Tren Insiden & Korban Bulanan</div>', unsafe_allow_html=True)
tren = a.tren_bulanan()
if not tren.empty and len(tren) > 1:
    tren_sorted = tren.sort_values(['Tahun', 'Bulan_Num']).copy()
    tren_sorted['Periode'] = tren_sorted['Bulan'] + '-' + tren_sorted['Tahun'].astype(str)
    fig_tren = go.Figure()
    fig_tren.add_trace(go.Bar(x=tren_sorted['Periode'], y=tren_sorted['Korban'],
        name='Jumlah Korban', marker=dict(color=BLUE_PRIMARY, opacity=0.75)))
    fig_tren.add_trace(go.Scatter(x=tren_sorted['Periode'], y=tren_sorted['Insiden'],
        name='Jumlah Insiden', mode='lines+markers',
        line=dict(color='#e07830', width=2.5),
        marker=dict(size=7, color='#e07830', line=dict(color='white', width=1.5)), yaxis='y2'))
    fig_tren.update_layout(**chart_layout(
        yaxis=dict(title='Jumlah Korban', gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR)),
        yaxis2=dict(title='Jumlah Insiden', overlaying='y', side='right', tickfont=dict(color=FONT_COLOR)),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR), tickangle=-30),
        legend=dict(orientation='h', y=1.08, font=dict(color=FONT_COLOR)),
        margin=dict(t=30, b=40, l=8, r=8)
    ))
    st.plotly_chart(fig_tren, use_container_width=True)

# ── Scatter ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🔬 Scatter: Jumlah Korban vs Skor Risiko</div>', unsafe_allow_html=True)
df_plot = df_filtered[df_filtered['Jumlah Korban'] > 0].copy()
if not df_plot.empty:
    hover_cols = [c for c in ['Provinsi', 'Kabupaten/Kota', 'Penyebab / Keterangan'] if c in df_plot.columns]
    fig_scatter = px.scatter(df_plot, x='Jumlah Korban', y='Skor Risiko',
        color='Kategori Risiko', size='Jumlah Korban', size_max=32,
        color_discrete_map={'Kritis': '#e03e5a', 'Tinggi': '#e07830', 'Sedang': '#c8970a', 'Rendah': '#1f9e5e'},
        hover_data=hover_cols,
        labels={'Jumlah Korban': 'Jumlah Korban', 'Skor Risiko': 'Skor Risiko (0–100)'})
    fig_scatter.update_layout(**chart_layout(
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR)),
        yaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR)),
        legend=dict(font=dict(color=FONT_COLOR))
    ))
    fig_scatter.update_traces(marker=dict(line=dict(color='white', width=1)))
    st.plotly_chart(fig_scatter, use_container_width=True)

# ── Tabel ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📋 Tabel Detail Risk Scoring</div>', unsafe_allow_html=True)
show_cols = ['No', 'Tanggal', 'Provinsi', 'Kabupaten/Kota', 'Jumlah Korban',
             'Kategori Penyebab', 'Kategori Risiko', 'Skor Risiko',
             'Skor_D1_Korban', 'Skor_D2_Patogen', 'Skor_D3_KLB',
             'Skor_D4_Rekurensi', 'Skor_D5_DataLengkap', 'Rekomendasi']
show_cols = [c for c in show_cols if c in df_filtered.columns]
df_show = df_filtered[show_cols].sort_values('Skor Risiko', ascending=False).reset_index(drop=True)
st.dataframe(df_show, use_container_width=True, height=420,
    column_config={
        'Skor Risiko': st.column_config.ProgressColumn('Skor Risiko', min_value=0, max_value=100, format='%d'),
        'Jumlah Korban': st.column_config.NumberColumn('Korban', format='%d'),
        'Skor_D1_Korban':      st.column_config.NumberColumn('D1', help='Skala Korban'),
        'Skor_D2_Patogen':     st.column_config.NumberColumn('D2', help='Patogen'),
        'Skor_D3_KLB':         st.column_config.NumberColumn('D3', help='KLB/Dampak'),
        'Skor_D4_Rekurensi':   st.column_config.NumberColumn('D4', help='Rekurensi'),
        'Skor_D5_DataLengkap': st.column_config.NumberColumn('D5', help='Kelengkapan Data'),
    })

# ── Download ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">⬇️ Download Hasil</div>', unsafe_allow_html=True)
col_d1, col_d2 = st.columns(2)
with col_d1:
    st.download_button("📥 Download Data Lengkap (CSV)",
        data=df_filtered.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
        file_name="hasil_report_mbg.csv", mime='text/csv', use_container_width=True)
with col_d2:
    st.download_button("📥 Download Detail Risiko (CSV)",
        data=df_show.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
        file_name="detail_risiko_mbg.csv", mime='text/csv', use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# CRUD SECTION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-title">🗂️ Manajemen Data </div>', unsafe_allow_html=True)

if 'df_edit' not in st.session_state or st.session_state.get('df_source') != uploaded.name:
    st.session_state['df_edit'] = df.copy()
    st.session_state['df_source'] = uploaded.name

df_edit = st.session_state['df_edit']

EDIT_COLS = ['No', 'Tanggal', 'Bulan', 'Tahun', 'Provinsi', 'Kabupaten/Kota',
             'Jumlah Korban', 'Penyebab / Keterangan']
EDIT_COLS = [c for c in EDIT_COLS if c in df_edit.columns]


def recalculate(df_in):
    calc = RiskCalculator()
    drop_cols = ['Skor Risiko', 'Kategori Risiko', 'Level Risiko', 'Rekomendasi',
                 'Skor_D1_Korban', 'Skor_D2_Patogen', 'Skor_D3_KLB',
                 'Skor_D4_Rekurensi', 'Skor_D5_DataLengkap',
                 'Kategori Penyebab', 'Flag_KLB', 'Flag_Disetop']
    df_in = df_in.drop(columns=[c for c in drop_cols if c in df_in.columns])
    return calc.calculate_all(df_in)


BULAN_LIST = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
              'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

crud_tab1, crud_tab2, crud_tab3 = st.tabs(["➕ Tambah Data", "✏️ Edit Data", "💾 Simpan & Download"])

# ── TAB 1: CREATE ─────────────────────────────────────────────────────────────
with crud_tab1:
    st.markdown("**Tambah insiden baru ke dataset:**")
    with st.form("form_tambah", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_no    = st.text_input("No", value=str(len(df_edit) + 1))
            new_tgl   = st.text_input("Tanggal", placeholder="cth: 15 Januari 2025")
            new_bulan = st.selectbox("Bulan", BULAN_LIST)
        with c2:
            new_tahun = st.text_input("Tahun", value="2025")
            new_prov  = st.text_input("Provinsi", placeholder="cth: Jawa Barat")
            new_kab   = st.text_input("Kabupaten/Kota", placeholder="cth: Kota Bandung")
        with c3:
            new_korban = st.number_input("Jumlah Korban", min_value=0, step=1)
            new_ket    = st.text_area("Penyebab / Keterangan", placeholder="cth: Dugaan kontaminasi bakteri...", height=100)

        if st.form_submit_button("➕ Tambah Insiden", use_container_width=True):
            new_row = {col: '' for col in df_edit.columns}
            new_row.update({
                'No': new_no, 'Tanggal': new_tgl, 'Bulan': new_bulan,
                'Tahun': new_tahun, 'Provinsi': new_prov,
                'Kabupaten/Kota': new_kab, 'Jumlah Korban': new_korban,
                'Penyebab / Keterangan': new_ket,
            })
            df_edit = pd.concat([df_edit, pd.DataFrame([new_row])], ignore_index=True)
            df_edit = recalculate(df_edit)
            st.session_state['df_edit'] = df_edit
            st.success(f"✅ Insiden baru berhasil ditambahkan! Total data: {len(df_edit)} baris")
            st.rerun()

# ── TAB 2: UPDATE & DELETE ────────────────────────────────────────────────────
with crud_tab2:
    st.markdown("**Pilih baris yang ingin diedit atau dihapus:**")

    selected_idx = st.selectbox(
        "Pilih baris:",
        options=df_edit.index.tolist(),
        format_func=lambda i: (
            f"[{i}] "
            f"{str(df_edit.at[i, 'Provinsi']) if 'Provinsi' in df_edit.columns else ''} — "
            f"{str(df_edit.at[i, 'Kabupaten/Kota']) if 'Kabupaten/Kota' in df_edit.columns else ''} — "
            f"{str(df_edit.at[i, 'Jumlah Korban']) if 'Jumlah Korban' in df_edit.columns else ''} korban"
        )
    )

    row = df_edit.loc[selected_idx]
    col_edit, col_del = st.columns([3, 1])

    with col_edit:
        st.markdown("**✏️ Edit data baris terpilih:**")
        with st.form("form_edit"):
            e1, e2, e3 = st.columns(3)
            with e1:
                e_no    = st.text_input("No", value=str(row.get('No', '')))
                e_tgl   = st.text_input("Tanggal", value=str(row.get('Tanggal', '')))
                cur_bulan = str(row.get('Bulan', ''))
                e_bulan = st.selectbox("Bulan", BULAN_LIST,
                    index=BULAN_LIST.index(cur_bulan) if cur_bulan in BULAN_LIST else 0)
            with e2:
                e_tahun = st.text_input("Tahun", value=str(row.get('Tahun', '')))
                e_prov  = st.text_input("Provinsi", value=str(row.get('Provinsi', '')))
                e_kab   = st.text_input("Kabupaten/Kota", value=str(row.get('Kabupaten/Kota', '')))
            with e3:
                e_korban = st.number_input("Jumlah Korban",
                    value=int(row.get('Jumlah Korban', 0) or 0), min_value=0, step=1)
                e_ket = st.text_area("Penyebab / Keterangan",
                    value=str(row.get('Penyebab / Keterangan', '')), height=100)

            if st.form_submit_button("💾 Simpan Perubahan", use_container_width=True):
                df_edit.at[selected_idx, 'No']                    = e_no
                df_edit.at[selected_idx, 'Tanggal']               = e_tgl
                df_edit.at[selected_idx, 'Bulan']                 = e_bulan
                df_edit.at[selected_idx, 'Tahun']                 = e_tahun
                df_edit.at[selected_idx, 'Provinsi']              = e_prov
                df_edit.at[selected_idx, 'Kabupaten/Kota']        = e_kab
                df_edit.at[selected_idx, 'Jumlah Korban']         = e_korban
                df_edit.at[selected_idx, 'Penyebab / Keterangan'] = e_ket
                df_edit = recalculate(df_edit)
                st.session_state['df_edit'] = df_edit
                st.success(f"✅ Baris [{selected_idx}] berhasil diperbarui!")
                st.rerun()

    with col_del:
        st.markdown("**🗑️ Hapus baris terpilih:**")
        st.markdown(f"""
        <div style='background:#fff5f5;border:1.5px solid #ffb3b3;border-radius:10px;padding:14px;margin-top:8px;'>
            <b>Baris [{selected_idx}]</b><br>
            {str(row.get('Provinsi', ''))} — {str(row.get('Kabupaten/Kota', ''))}<br>
            <span style='color:#e03e5a;font-weight:700;'>{str(row.get('Jumlah Korban', ''))} korban</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        confirm_del = st.checkbox("Saya yakin ingin menghapus baris ini")
        if st.button("🗑️ Hapus Baris", use_container_width=True, type="primary", disabled=not confirm_del):
            df_edit = df_edit.drop(index=selected_idx).reset_index(drop=True)
            df_edit = recalculate(df_edit)
            st.session_state['df_edit'] = df_edit
            st.success(f"✅ Baris [{selected_idx}] berhasil dihapus! Sisa: {len(df_edit)} baris")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Preview data setelah edit:**")
    preview_cols = [c for c in EDIT_COLS + ['Kategori Risiko', 'Skor Risiko'] if c in df_edit.columns]
    st.dataframe(df_edit[preview_cols].reset_index(drop=True), use_container_width=True, height=300)

# ── TAB 3: SAVE & DOWNLOAD ────────────────────────────────────────────────────
with crud_tab3:
    st.info(f"📊 Dataset saat ini: **{len(df_edit)} baris** setelah semua perubahan CRUD.")
    col_s1, col_s2 = st.columns(2)

    with col_s1:
        st.markdown("**💾 Simpan ke file lokal:**")
        save_filename = st.text_input("Nama file CSV:", value=DEFAULT_CSV)
        if st.button("💾 Simpan ke Lokal", use_container_width=True):
            try:
                df_edit.to_csv(save_filename, index=False, encoding='utf-8-sig')
                st.success(f"✅ Disimpan ke: `{save_filename}`")
            except Exception as e:
                st.error(f"❌ Gagal simpan: {e}")

    with col_s2:
        st.markdown("**📥 Download sebagai CSV:**")
        st.download_button("📥 Download Data Hasil Edit",
            data=df_edit.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
            file_name="data_mbg_edited.csv", mime='text/csv', use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        dl_cols = ['No', 'Tanggal', 'Bulan', 'Tahun', 'Provinsi', 'Kabupaten/Kota',
                   'Jumlah Korban', 'Penyebab / Keterangan', 'Kategori Risiko', 'Skor Risiko', 'Rekomendasi']
        dl_cols = [c for c in dl_cols if c in df_edit.columns]
        st.download_button("📥 Download Ringkasan Risiko",
            data=df_edit[dl_cols].sort_values('Skor Risiko', ascending=False)
                .to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
            file_name="ringkasan_risiko_mbg.csv", mime='text/csv', use_container_width=True)

st.markdown('<div class="footer">MBG Risk Scoring System &nbsp;|&nbsp; Data: BGN / BPOM / Media Terverifikasi</div>', unsafe_allow_html=True)