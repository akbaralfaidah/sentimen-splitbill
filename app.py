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
        }
    </style>
""", unsafe_allow_html=True)

# --- JUDUL APLIKASI ---
st.title("📊 Analisis Sentimen Isu Split Bill")

# --- INITIALIZE SESSION STATE ---
if 'page_number' not in st.session_state:
    st.session_state.page_number = 1

def reset_page():
    st.session_state.page_number = 1

# --- SIDEBAR: INPUT DATA ---
with st.sidebar:
    st.header("🔍 Filter Pencarian")
    
    keyword = st.text_input("Kata Kunci (Wajib)", value="dibayarin", help="Masukkan kata yang ingin dianalisis", on_change=reset_page)
    
    exclude_word = st.text_input("Kecualikan Kata (Opsional)", value="KUA", help="Kata yang tidak boleh ada dalam tweet", on_change=reset_page)
    
    st.markdown("---")
    st.header("⚙️ Pengaturan Tabel")
    
    limit_rows = st.selectbox(
        "Baris per Halaman",
        options=[10, 20, 50, 100],
        index=0,
        help="Pilih berapa banyak data yang ingin ditampilkan dalam satu halaman.",
        on_change=reset_page
    )
    
    st.caption("*Tekan Enter setelah mengetik kata kunci untuk memperbarui.*")

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
    st.error("❌ File 'HASIL_AKHIR_SKOR_POLARITAS.csv' tidak ditemukan. Pastikan file ada di folder yang sama.")
else:
    # 1. Filter Data
    if keyword:
        mask_include = df['text'].str.contains(r'\b' + re.escape(keyword) + r'\b', case=False, regex=True, na=False)
        
        if exclude_word:
            mask_exclude = df['text'].str.contains(r'\b' + re.escape(exclude_word) + r'\b', case=False, regex=True, na=False)
            df_filtered = df[mask_include & ~mask_exclude].copy()
            st.info(f"Menampilkan hasil untuk kata kunci: **'{keyword}'** (tanpa kata **'{exclude_word}'**)")
        else:
            df_filtered = df[mask_include].copy()
            st.info(f"Menampilkan hasil untuk kata kunci: **'{keyword}'**")

        # 2. Kategorisasi Sentimen
        def categorize_sentiment(score):
            if score > 0: return 'Positive'
            elif score < 0: return 'Negative'
            else: return 'Neutral'

        if not df_filtered.empty:
            df_filtered['sentimen_kategori'] = df_filtered['skor_polaritas'].apply(categorize_sentiment)

            # --- BAGIAN 1: STATISTIK ---
            st.subheader("1. Statistik")
            
            col1, col2, col3, col4 = st.columns(4)
            
            total_tweet = len(df_filtered)
            counts = df_filtered['sentimen_kategori'].value_counts()
            
            def get_count(cat): return counts.get(cat, 0)
            def get_pct(cat): return (get_count(cat) / total_tweet * 100) if total_tweet > 0 else 0

            with col1:
                st.metric("Total Tweet", f"{total_tweet}")
            with col2:
                st.metric("Positive", f"{get_count('Positive')}", f"{get_pct('Positive'):.1f}%")
            with col3:
                st.metric("Neutral", f"{get_count('Neutral')}", f"{get_pct('Neutral'):.1f}%", delta_color="off")
            with col4:
                st.metric("Negative", f"{get_count('Negative')}", f"{get_pct('Negative'):.1f}%", delta_color="inverse")

            # --- BAGIAN 2: EKSPLORASI DATA ---
            st.markdown("---")
            st.subheader(f"2. Eksplorasi Data")
            
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
                
                batch_df = dataset.iloc[start_idx:end_idx].copy()
                
                # Pembulatan Data
                batch_df['skor_polaritas'] = batch_df['skor_polaritas'].round(4)

                calc_height = (len(batch_df) * 35) + 38
                
                # TAMPILKAN TABEL
                st.dataframe(
                    # === DI SINI PERUBAHANNYA (URUTAN KOLOM) ===
                    batch_df[['text', 'skor_polaritas', 'sentimen_kategori']], 
                    use_container_width=True, 
                    hide_index=True,
                    height=calc_height,
                    column_config={
                        "text": st.column_config.TextColumn("Tweet", width="large"),
                        "skor_polaritas": st.column_config.NumberColumn("Skor"),
                        "sentimen_kategori": st.column_config.TextColumn("Label", width="small")
                    }
                )
                
                st.markdown(f"<div class='page-info'>Halaman {current_page} dari {total_pages} (Total: {total_rows} data)</div>", unsafe_allow_html=True)
                
                col_prev, col_spacer, col_next = st.columns([1, 4, 1])
                with col_prev:
                    if st.button("⬅️ Sebelumnya", key=f"{key_prefix}_prev", disabled=(current_page == 1)):
                        st.session_state.page_number -= 1
                        st.rerun()
                with col_next:
                    if st.button("Selanjutnya ➡️", key=f"{key_prefix}_next", disabled=(current_page == total_pages)):
                        st.session_state.page_number += 1
                        st.rerun()

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
            
    else:
        st.info("👈 Silakan masukkan kata kunci di sidebar kiri untuk memulai analisis.")

