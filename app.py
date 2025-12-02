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
        
        .search-result {
            padding: 15px;
            background-color: #e3f2fd;
            border-left: 5px solid #2196f3;
            margin-bottom: 20px;
            border-radius: 4px;
            color: #0d47a1;
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

# --- MANAJEMEN STATE TERPISAH (SOLUSI BUG PAGINATION) ---
# Setiap tab punya ingatan halaman sendiri-sendiri
if 'page_all' not in st.session_state: st.session_state.page_all = 1
if 'page_neg' not in st.session_state: st.session_state.page_neg = 1
if 'page_pos' not in st.session_state: st.session_state.page_pos = 1
if 'page_net' not in st.session_state: st.session_state.page_net = 1

def reset_all_pages():
    st.session_state.page_all = 1
    st.session_state.page_neg = 1
    st.session_state.page_pos = 1
    st.session_state.page_net = 1

# Fungsi khusus untuk tombol loncat (Locator)
def jump_to_page_all(target_page):
    st.session_state.page_all = target_page

# Callback navigasi generik
def change_page(key, delta):
    st.session_state[key] += delta

# --- SIDEBAR: INPUT DATA ---
with st.sidebar:
    st.header("🔍 Mode 1: Filter Data")
    st.caption("Gunakan ini untuk menyaring data.")
    
    # Filter Data (Reset halaman jika filter berubah)
    filter_keyword = st.text_input("Filter Kata", value="", placeholder="Hanya tampilkan yang berisi...", on_change=reset_all_pages)
    exclude_word = st.text_input("Kecualikan Kata", value="", placeholder="Contoh: KUA", on_change=reset_all_pages)
    
    st.markdown("---")
    st.header("🔎 Mode 2: Cari Posisi")
    st.caption("Cari lokasi data di tab 'All Data'.")
    
    locator_keyword = st.text_input("Cari Lokasi Kata", value="", placeholder="Ketik kata...")
    
    st.markdown("---")
    st.header("⚙️ Pengaturan Tabel")
    
    limit_rows = st.selectbox(
        "Baris per Halaman",
        options=[10, 20, 50, 100],
        index=0,
        on_change=reset_all_pages
    )

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('HASIL_AKHIR_SKOR_POLARITAS_V2.csv')
        return df
    except FileNotFoundError:
        return None

df = load_data()

# --- LOGIKA UTAMA ---
if df is None:
    st.error("❌ File 'HASIL_AKHIR_SKOR_POLARITAS.csv' tidak ditemukan.")
else:
    # 1. Logika Filter Data
    # case=False MEMBUAT PENCARIAN HURUF BESAR/KECIL SAMA SAJA
    if filter_keyword:
        mask_include = df['text'].str.contains(r'\b' + re.escape(filter_keyword) + r'\b', case=False, regex=True, na=False)
    else:
        mask_include = pd.Series([True] * len(df))
        
    if exclude_word:
        mask_exclude = df['text'].str.contains(r'\b' + re.escape(exclude_word) + r'\b', case=False, regex=True, na=False)
        df_filtered = df[mask_include & ~mask_exclude].copy()
    else:
        df_filtered = df[mask_include].copy()

    # Info Filter
    if filter_keyword:
        st.info(f"🔹 Mode Filter Aktif: Menampilkan data dengan kata **'{filter_keyword}'**.")
    else:
        st.success("🔹 Menampilkan **SELURUH DATA** (Default).")

    # 2. Kategorisasi Sentimen
    def categorize_sentiment(score):
        if score > 0: return 'Positive'
        elif score < 0: return 'Negative'
        else: return 'Neutral'

    if not df_filtered.empty:
        df_filtered['sentimen_kategori'] = df_filtered['skor_polaritas'].apply(categorize_sentiment)

        # --- HITUNG RATA-RATA POLARITAS (FITUR BARU) ---
        avg_polarity = df_filtered['skor_polaritas'].mean()
        
        # Tentukan kategori rata-rata
        if avg_polarity > 0:
            avg_cat = "Positive"
            avg_color = "green"
        elif avg_polarity < 0:
            avg_cat = "Negative"
            avg_color = "red"
        else:
            avg_cat = "Neutral"
            avg_color = "gray"

        # 3. LOGIKA PENCARI POSISI (LOCATOR)
        if locator_keyword:
            # case=False MEMBUAT PENCARIAN HURUF BESAR/KECIL SAMA SAJA
            matches = df_filtered[df_filtered['text'].str.contains(r'\b' + re.escape(locator_keyword) + r'\b', case=False, regex=True, na=False)]
            
            if not matches.empty:
                first_match_idx = matches.index[0] # Index asli
                
                # Cari posisi relatif (0-based)
                df_reset = df_filtered.reset_index()
                match_loc = df_reset[df_reset['index'] == first_match_idx].index[0]
                
                # Hitung Nomor Urut (1-based) dan Halaman Target
                nomor_urut = match_loc + 1
                target_page = math.ceil(nomor_urut / limit_rows)
                
                col_loc1, col_loc2 = st.columns([3, 1])
                with col_loc1:
                    st.markdown(f"""
                    <div class="search-result">
                        <b>✅ Ditemukan!</b> Kata <b>"{locator_keyword}"</b> ada di Data Nomor <b>{nomor_urut}</b> (Halaman <b>{target_page}</b> Tab 'All Data').
                    </div>
                    """, unsafe_allow_html=True)
                with col_loc2:
                    # CALLBACK KHUSUS: Update hanya 'page_all'
                    st.button(f"🚀 Pergi ke Hal {target_page}", on_click=jump_to_page_all, args=(target_page,), type="primary")
            else:
                st.error(f"❌ Kata '{locator_keyword}' tidak ditemukan dalam data yang sedang ditampilkan.")

        # --- BAGIAN STATISTIK (DIPERBARUI DENGAN RATA-RATA) ---
        st.subheader("1. Statistik Ringkas")
        
        # Gunakan 5 kolom agar muat untuk rata-rata
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_tweet = len(df_filtered)
        counts = df_filtered['sentimen_kategori'].value_counts()
        
        def get_count(cat): return counts.get(cat, 0)
        def get_pct(cat): return (get_count(cat) / total_tweet * 100) if total_tweet > 0 else 0

        with col1: st.metric("Total Data", f"{total_tweet}")
        with col2: st.metric("Positive", f"{get_count('Positive')}", f"{get_pct('Positive'):.1f}%")
        with col3: st.metric("Neutral", f"{get_count('Neutral')}", f"{get_pct('Neutral'):.1f}%", delta_color="off")
        with col4: st.metric("Negative", f"{get_count('Negative')}", f"{get_pct('Negative'):.1f}%", delta_color="inverse")
        
        # Kolom Baru: Rata-Rata Polaritas
        with col5:
            st.metric("Rata-Rata Skor", f"{avg_polarity:.4f}", f"{avg_cat}")

        # --- BAGIAN TABEL ---
        st.markdown("---")
        st.subheader("2. Data Tabel")
        
        # Tab
        tab_neg, tab_pos, tab_net, tab_all = st.tabs(["🔴 Negative", "🟢 Positive", "⚪ Neutral", "📂 All Data"])
        
        def paginated_dataframe(dataset, key_prefix):
            if dataset.empty:
                st.write("Tidak ada data.")
                return

            # Menggunakan kunci state yang berbeda untuk setiap tab (page_all, page_neg, dll)
            state_key = f"page_{key_prefix}"

            total_rows = len(dataset)
            total_pages = math.ceil(total_rows / limit_rows)
            
            # PROTEKSI HALAMAN: Reset ke 1 jika halaman saat ini melebihi total halaman (misal abis filter data)
            if st.session_state[state_key] > total_pages:
                st.session_state[state_key] = 1
            
            current_page = st.session_state[state_key]
            
            start_idx = (current_page - 1) * limit_rows
            end_idx = start_idx + limit_rows
            
            # Slice Data
            batch_df = dataset.iloc[start_idx:end_idx].copy()
            batch_df['skor_polaritas'] = batch_df['skor_polaritas'].round(4)
            
            # Nomor Urut Relatif
            batch_df.insert(0, 'No', range(start_idx + 1, start_idx + len(batch_df) + 1))

            calc_height = (len(batch_df) * 35) + 38
            
            # Tabel
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
            
            # Tombol Navigasi memanggil change_page dengan kunci spesifik tab ini
            with col_prev:
                st.button("⬅️ Sebelumnya", key=f"prev_{key_prefix}", on_click=change_page, args=(state_key, -1), disabled=(current_page == 1))
            
            with col_next:
                st.button("Selanjutnya ➡️", key=f"next_{key_prefix}", on_click=change_page, args=(state_key, 1), disabled=(current_page == total_pages))

        # Render Tabs (Kirim kode unik: neg, pos, net, all)
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
            paginated_dataframe(df_filtered, "all")

    else:
        st.warning("⚠️ Tidak ditemukan tweet yang cocok dengan filter tersebut.")
