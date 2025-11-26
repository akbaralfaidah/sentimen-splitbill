import streamlit as st
import pandas as pd
import re
import math

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Analisis Sentimen Skripsi",
    page_icon="📊",
    layout="wide"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

        html, body, [class*="css"]  {
            font-family: 'Poppins', sans-serif;
        }
        
        h1, h2, h3 {
            font-weight: 700;
            color: #2C3E50;
        }
        
        .stDataFrame {
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        
        div[data-testid="metric-container"] {
            background-color: #F8F9FA;
            border: 1px solid #E9ECEF;
            padding: 10px;
            border-radius: 8px;
            color: #2C3E50;
        }
        
        .page-info {
            text-align: center;
            font-weight: 600;
            margin-top: 10px;
            font-size: 14px;
            color: #555;
        }
    </style>
""", unsafe_allow_html=True)

# --- JUDUL APLIKASI ---
st.title("📊 Analisis Sentimen Isu Split Bill")

# --- INITIALIZE SESSION STATE ---
if 'page_number' not in st.session_state:
    st.session_state.page_number = 1

# Fungsi Callback untuk Pagination
def next_page():
    st.session_state.page_number += 1

def prev_page():
    st.session_state.page_number -= 1

def reset_page():
    st.session_state.page_number = 1

# --- SIDEBAR: FILTER & PENCARIAN ---
with st.sidebar:
    st.header("🔍 Filter & Pencarian")
    
    # 1. Input Kata Kunci (Fitur Cari Utama)
    keyword = st.text_input(
        "Cari Tweet (Keyword)", 
        value="", 
        placeholder="Ketik kata kunci...", 
        help="Ketik kata untuk memfilter data (biarkan kosong untuk melihat semua)", 
        on_change=reset_page
    )
    
    # 2. Input Exclude
    exclude_word = st.text_input(
        "Kecualikan Kata (Opsional)", 
        value="", 
        placeholder="Contoh: KUA", 
        help="Tweet yang mengandung kata ini tidak akan ditampilkan", 
        on_change=reset_page
    )
    
    st.markdown("---")
    st.header("⚙️ Pengaturan Tabel")
    
    limit_rows = st.selectbox(
        "Baris per Halaman",
        options=[10, 20, 50, 100],
        index=0,
        help="Pilih berapa banyak data yang ingin ditampilkan dalam satu halaman.",
        on_change=reset_page
    )
    
    st.caption("*Tekan Enter pada keyboard setelah mengetik untuk mencari.*")

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('HASIL_AKHIR_SKOR_POLARITAS.csv')
        return df
    except FileNotFoundError:
        return None

df = load_data()

# --- LOGIKA UTAMA ---
if df is None:
    st.error("❌ File 'HASIL_AKHIR_SKOR_POLARITAS.csv' tidak ditemukan. Pastikan file ada di folder yang sama.")
else:
    # 1. Logika Filter (Pencarian)
    if keyword:
        mask_include = df['text'].str.contains(r'\b' + re.escape(keyword) + r'\b', case=False, regex=True, na=False)
    else:
        mask_include = pd.Series([True] * len(df)) # Ambil semua jika keyword kosong
        
    if exclude_word:
        mask_exclude = df['text'].str.contains(r'\b' + re.escape(exclude_word) + r'\b', case=False, regex=True, na=False)
        df_filtered = df[mask_include & ~mask_exclude].copy()
        
        if keyword:
            st.info(f"🔍 Menampilkan hasil pencarian: **'{keyword}'** (tanpa kata **'{exclude_word}'**)")
        else:
            st.info(f"📂 Menampilkan **SEMUA DATA** (tanpa kata **'{exclude_word}'**)")
    else:
        df_filtered = df[mask_include].copy()
        if keyword:
            st.info(f"🔍 Menampilkan hasil pencarian: **'{keyword}'**")
        else:
            st.success("📂 Menampilkan **SELURUH DATA** (Default)")

    # 2. Kategorisasi Sentimen
    def categorize_sentiment(score):
        if score > 0: return 'Positive'
        elif score < 0: return 'Negative'
        else: return 'Neutral'

    if not df_filtered.empty:
        df_filtered['sentimen_kategori'] = df_filtered['skor_polaritas'].apply(categorize_sentiment)

        # --- BAGIAN 1: STATISTIK ---
        st.subheader("1. Statistik Ringkas")
        
        col1, col2, col3, col4 = st.columns(4)
        total_tweet = len(df_filtered)
        counts = df_filtered['sentimen_kategori'].value_counts()
        
        def get_count(cat): return counts.get(cat, 0)
        def get_pct(cat): return (get_count(cat) / total_tweet * 100) if total_tweet > 0 else 0

        with col1: st.metric("Total Data", f"{total_tweet}")
        with col2: st.metric("Positive", f"{get_count('Positive')}", f"{get_pct('Positive'):.1f}%")
        with col3: st.metric("Neutral", f"{get_count('Neutral')}", f"{get_pct('Neutral'):.1f}%", delta_color="off")
        with col4: st.metric("Negative", f"{get_count('Negative')}", f"{get_pct('Negative'):.1f}%", delta_color="inverse")

        # --- BAGIAN 2: EKSPLORASI DATA ---
        st.markdown("---")
        st.subheader(f"2. Data Tabel")
        
        tab_neg, tab_pos, tab_net, tab_all = st.tabs(["🔴 Negative", "🟢 Positive", "⚪ Neutral", "📂 All Data"])
        
        def paginated_dataframe(dataset, key_prefix):
            if dataset.empty:
                st.write("Tidak ada data.")
                return

            total_rows = len(dataset)
            total_pages = math.ceil(total_rows / limit_rows)
            
            if st.session_state.page_number > total_pages:
                st.session_state.page_number = 1
            
            current_page = st.session_state.page_number
            start_idx = (current_page - 1) * limit_rows
            end_idx = start_idx + limit_rows
            
            # --- PERSIAPAN DATA UNTUK TABEL ---
            batch_df = dataset.iloc[start_idx:end_idx].copy()
            
            # 1. Bulatkan Skor
            batch_df['skor_polaritas'] = batch_df['skor_polaritas'].round(4)
            
            # 2. Tambahkan Kolom Nomor (No)
            # Nomor dimulai dari start_idx + 1 agar berlanjut antar halaman (misal hal 2 mulai dr 11)
            batch_df.insert(0, 'No', range(start_idx + 1, start_idx + len(batch_df) + 1))

            # Hitung tinggi tabel agar scroll halaman (bukan scroll tabel)
            calc_height = (len(batch_df) * 35) + 38
            
            # --- TAMPILKAN DATAFRAME ---
            st.dataframe(
                batch_df[['No', 'text', 'sentimen_kategori', 'skor_polaritas']], 
                use_container_width=True, 
                hide_index=True,
                height=calc_height,
                column_config={
                    "No": st.column_config.NumberColumn("No", width="small"),
                    "text": st.column_config.TextColumn("Tweet", width="large"),
                    "sentimen_kategori": st.column_config.TextColumn("Label", width="small"),
                    "skor_polaritas": st.column_config.NumberColumn("Skor")
                }
            )
            
            # --- KONTROL PAGINATION ---
            st.markdown(f"<div class='page-info'>Halaman {current_page} dari {total_pages} (Total: {total_rows} data)</div>", unsafe_allow_html=True)
            
            col_prev, col_spacer, col_next = st.columns([1, 4, 1])
            with col_prev:
                st.button("⬅️ Sebelumnya", key=f"{key_prefix}_prev", on_click=prev_page, disabled=(current_page == 1))
            
            with col_next:
                st.button("Selanjutnya ➡️", key=f"{key_prefix}_next", on_click=next_page, disabled=(current_page == total_pages))

        with tab_neg:
            st.markdown("##### Data Negative")
            df_neg = df_filtered[df_filtered['sentimen_kategori'] == 'Negative'].sort_values('skor_polaritas', ascending=True)
            paginated_dataframe(df_neg, "neg")
            
        with tab_pos:
            st.markdown("##### Data Positive")
            df_pos = df_filtered[df_filtered['sentimen_kategori'] == 'Positive'].sort_values('skor_polaritas', ascending=False)
            paginated_dataframe(df_pos, "pos")
            
        with tab_net:
            st.markdown("##### Data Neutral")
            df_net = df_filtered[df_filtered['sentimen_kategori'] == 'Neutral']
            paginated_dataframe(df_net, "net")

        with tab_all:
            st.markdown("##### Semua Data (Terfilter)")
            paginated_dataframe(df_filtered, "all")

    else:
        st.warning("⚠️ Tidak ditemukan tweet yang cocok dengan filter tersebut.")
