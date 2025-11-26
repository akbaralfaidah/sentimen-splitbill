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
        
        /* Style untuk Info Pencarian */
        .search-result {
            padding: 10px;
            background-color: #e8f4f8;
            border-left: 5px solid #3498db;
            margin-bottom: 20px;
            border-radius: 4px;
            color: #2980b9;
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

def set_page(page):
    st.session_state.page_number = page

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('HASIL_AKHIR_SKOR_POLARITAS_V2.csv')
        return df
    except FileNotFoundError:
        return None

df = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Mode 1: Filter Data")
    st.caption("Gunakan ini untuk menyaring data.")
    
    # 1. Filter Data (Lama)
    filter_keyword = st.text_input("Filter Kata", value="", placeholder="Hanya tampilkan yang berisi...", on_change=reset_page)
    exclude_word = st.text_input("Kecualikan Kata", value="", placeholder="Contoh: KUA", on_change=reset_page)
    
    st.markdown("---")
    st.header("🔎 Mode 2: Cari Posisi (Locator)")
    st.caption("Cari nomor urut data tanpa memfilter.")
    
    # 2. Pencari Posisi (Baru)
    locator_keyword = st.text_input("Cari Lokasi Kata", value="", placeholder="Ketik kata untuk dicari posisinya...")
    
    st.markdown("---")
    st.header("⚙️ Pengaturan Tabel")
    
    limit_rows = st.selectbox(
        "Baris per Halaman",
        options=[10, 20, 50, 100],
        index=0,
        on_change=reset_page
    )

# --- LOGIKA UTAMA ---
if df is None:
    st.error("❌ File 'HASIL_AKHIR_SKOR_POLARITAS.csv' tidak ditemukan.")
else:
    # 1. Logika Filter
    if filter_keyword:
        mask_include = df['text'].str.contains(r'\b' + re.escape(filter_keyword) + r'\b', case=False, regex=True, na=False)
    else:
        mask_include = pd.Series([True] * len(df))
        
    if exclude_word:
        mask_exclude = df['text'].str.contains(r'\b' + re.escape(exclude_word) + r'\b', case=False, regex=True, na=False)
        df_filtered = df[mask_include & ~mask_exclude].copy()
    else:
        df_filtered = df[mask_include].copy()

    # Informasi Mode
    if filter_keyword:
        st.info(f"🔹 Mode Filter Aktif: Menampilkan data yang mengandung **'{filter_keyword}'**.")
    else:
        st.success("🔹 Menampilkan **SELURUH DATA** (Default).")

    # 2. Kategorisasi Sentimen
    def categorize_sentiment(score):
        if score > 0: return 'Positive'
        elif score < 0: return 'Negative'
        else: return 'Neutral'

    if not df_filtered.empty:
        df_filtered['sentimen_kategori'] = df_filtered['skor_polaritas'].apply(categorize_sentiment)

        # 3. LOGIKA PENCARI POSISI (LOCATOR)
        if locator_keyword:
            # Cari index pertama yang mengandung kata tersebut di dalam data yang sudah terfilter
            matches = df_filtered[df_filtered['text'].str.contains(r'\b' + re.escape(locator_keyword) + r'\b', case=False, regex=True, na=False)]
            
            if not matches.empty:
                first_match_idx = matches.index[0] # Index asli dataframe
                
                # Cari posisi urut relatif dalam data terfilter
                # Kita reset index dulu untuk dapat nomor urut (0, 1, 2...)
                df_reset = df_filtered.reset_index()
                match_loc = df_reset[df_reset['index'] == first_match_idx].index[0]
                
                # Hitung Nomor Urut (mulai dari 1)
                nomor_urut = match_loc + 1
                
                # Hitung Halaman
                target_page = math.ceil(nomor_urut / limit_rows)
                
                st.markdown(f"""
                <div class="search-result">
                    <b>✅ Ditemukan!</b> Kata <b>"{locator_keyword}"</b> pertama kali muncul pada: <br>
                    • <b>Nomor Urut:</b> {nomor_urut} <br>
                    • <b>Halaman:</b> {target_page}
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🚀 Pergi ke Halaman {target_page}"):
                    set_page(target_page)
                    st.rerun()
            else:
                st.error(f"❌ Kata '{locator_keyword}' tidak ditemukan dalam data yang sedang ditampilkan.")

        # --- BAGIAN TABEL & PAGINATION ---
        st.subheader(f"Data Tabel")
        
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
            
            # Data Slice
            batch_df = dataset.iloc[start_idx:end_idx].copy()
            
            # Formatting
            batch_df['skor_polaritas'] = batch_df['skor_polaritas'].round(4)
            
            # Tambah Kolom No (Nomor Urut Global)
            # Kita harus tahu index ini relatif terhadap apa.
            # Jika di tab "All Data", No = index di df_filtered
            # Jika di tab "Negative", No = urutan di dalam filter negatif
            
            # Agar konsisten, kita buat nomor urut berdasarkan posisi di tabel yang sedang dilihat
            batch_df.insert(0, 'No', range(start_idx + 1, start_idx + len(batch_df) + 1))

            calc_height = (len(batch_df) * 35) + 38
            
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
            
            st.markdown(f"<div class='page-info'>Halaman {current_page} dari {total_pages} (Total: {total_rows} data)</div>", unsafe_allow_html=True)
            
            col_prev, col_spacer, col_next = st.columns([1, 4, 1])
            with col_prev:
                st.button("⬅️ Sebelumnya", key=f"{key_prefix}_prev", on_click=prev_page, disabled=(current_page == 1))
            
            with col_next:
                st.button("Selanjutnya ➡️", key=f"{key_prefix}_next", on_click=next_page, disabled=(current_page == total_pages))

        with tab_neg:
            df_neg = df_filtered[df_filtered['sentimen_kategori'] == 'Negative'].sort_values('skor_polaritas', ascending=True)
            paginated_dataframe(df_neg, "neg")
            
        with tab_pos:
            df_pos = df_filtered[df_filtered['sentimen_kategori'] == 'Positive'].sort_values('skor_polaritas', ascending=False)
            paginated_dataframe(df_pos, "pos")
            
        with tab_net:
            df_net = df_filtered[df_filtered['sentimen_kategori'] == 'Neutral']
            paginated_dataframe(df_net, "net")

        with tab_all:
            # Default sort index agar urutan stabil
            paginated_dataframe(df_filtered, "all")

    else:
        st.warning("⚠️ Tidak ditemukan tweet yang cocok dengan filter tersebut.")
