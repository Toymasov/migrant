import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# *****************************************************************
# 🛠️ 1-O'ZGARTIRISH: TOKEN VA UID KODNING O'ZIDA BERILADI
# *****************************************************************
API_TOKEN = "32d9554c1adff54adcfec52a29993af01e28bd33" # <--- TOKEN
ASSET_UID = "a8hjj8Ehj5eTW5GjS28tR6"     # <--- UID
# *****************************************************************

# 🛠️ 2-O'ZGARTIRISH: SERVER TURI HARDCODE QILINDI (FAQAT GLOBAL)
BASE_URL = "https://kf.kobotoolbox.org"
api_url = f"{BASE_URL}/api/v2/assets/{ASSET_UID}/data.json"


# 1. Sahifa sozlamalari
st.set_page_config(
    page_title="KoboToolbox Global Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Migrantlar savolnomasi live time tahlili")

# Session State boshlash
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

# 2. Yon panel (Sidebar) - Endi faqat yuklash tugmasi qoldi
st.sidebar.header("⚙️ Sozlamalar")

# 3. Ma'lumotlarni yuklash funksiyasi (Keshlash bilan)
@st.cache_data(ttl=300) 
def load_data(url, token):
    headers = {"Authorization": f"Token {token}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        data = response.json()
        df = pd.DataFrame(data['results'])
        
        if '_submission_time' in df.columns:
            # Vaqtga o'tkazish
            df['_submission_time'] = pd.to_datetime(df['_submission_time'], errors='coerce')
            
            # 🚀 TO'G'IRLASH: UTC+5 (Toshkent vaqtiga o'tkazish)
            if df['_submission_time'].dt.tz is None: 
                # 1. UTC deb belgilash (ERROR='COERCE' O'CHIRILDI)
                # 2. Keyin 'Asia/Tashkent' (UTC+5) ga o'tkazish
                
                # df['_submission_time'] = df['_submission_time'].dt.tz_localize('UTC', errors='coerce').dt.tz_convert('Asia/Tashkent') # <--- ESKI XATOLIK BERUVCHI QATOR
                
                df['_submission_time'] = df['_submission_time'].dt.tz_localize('UTC').dt.tz_convert('Asia/Tashkent') # <--- YANGI TO'G'RI QATOR
            else:
                # Agar allaqachon biror vaqt zonasi bo'lsa, faqat Toshkentga o'tkazamiz
                df['_submission_time'] = df['_submission_time'].dt.tz_convert('Asia/Tashkent')
            
        return df
    except Exception as e:
        # Xatolikni aniqroq ko'rsatish uchun e ni formatlaymiz
        st.error(f"Ma'lumotlarni yuklashda xatolik yuz berdi. Xato: {e}")
        return pd.DataFrame()

# 4. Tugmani bosish logikasi: Ma'lumotni yuklash va Session Statega saqlash
def handle_load_data():
    with st.spinner("Ma'lumotlar yuklanmoqda..."):
        new_df = load_data(api_url, API_TOKEN) 
        st.session_state.df = new_df

# Tugma yon panelda ishlaydi
st.sidebar.button("Ma'lumotlarni yuklash", on_click=handle_load_data)

# 5. Asosiy Vizualizatsiya Qismi (YANGI, FILTRLAR BILAN)
df = st.session_state.df

if not df.empty:
    st.success(f"Ma'lumotlar yuklandi. Jami {len(df)} ta so'rovnoma.")

    # Tahlil uchun yaroqli ustunlar ro'yxatini tayyorlash
    clean_columns = [c for c in df.columns if not c.startswith('_') and not c.startswith('meta/')]
    
    # ----------------------------------------------------
    # 🔎 IKKI BOSQICHLI FILTRLAR QISMI (YANGI QO'SHILDI)
    # ----------------------------------------------------
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔎 Kaskadli Filtrlar")
    
    # --- FILTR 1: Birlamchi tanlov (Parent Filter) ---
    filter_col_1 = st.sidebar.selectbox(
        "1. Birlamchi Filtr ustunini tanlang:", 
        clean_columns, 
        key='f1_col',
        index=0 # Default birinchi ustunni tanlash
    )
    
    # Filtr qiymatlarini tanlash
    if filter_col_1:
        # 1-Filtr uchun barcha variantlar (butun ma'lumotdan olinadi)
        unique_values_1 = df[filter_col_1].dropna().unique().tolist()
        selected_values_1 = st.sidebar.multiselect(
            f"1. **{filter_col_1}** bo'yicha saralash:", 
            unique_values_1, 
            default=unique_values_1,
            key='f1_val'
        )
        
        # Birlamchi Filtrni qo'llash
        df_intermediate = df[df[filter_col_1].isin(selected_values_1)]
        
        # --- FILTR 2: Ikkilamchi tanlov (Child/Nested Filter) ---
        st.sidebar.markdown("---")
        
        filter_col_2 = st.sidebar.selectbox(
            "2. Ikkilamchi Filtr ustunini tanlang:", 
            clean_columns, 
            key='f2_col',
            index=1 if len(clean_columns) > 1 else 0 # Default ikkinchi ustunni tanlash
        )
        
        if filter_col_2:
            # 2-Filtr variantlari FAQQAT 1-filtr tanloviga bog'liq bo'ladi!
            unique_values_2 = df_intermediate[filter_col_2].dropna().unique().tolist()
            selected_values_2 = st.sidebar.multiselect(
                f"2. **{filter_col_2}** bo'yicha saralash:", 
                unique_values_2, 
                default=unique_values_2,
                key='f2_val'
            )
            
            # Ikkilamchi Filtrni qo'llash
            df_final = df_intermediate[df_intermediate[filter_col_2].isin(selected_values_2)]
        else:
            df_final = df_intermediate # Agar 2-filtr tanlanmasa, 1-filtr natijasi qoladi
            
    else:
        df_final = df # Agar hech qanday filtr tanlanmasa
    
    st.info(f"Hozirda **{len(df_final)}** ta so'rovnoma ko'rsatilmoqda. (Filtrlar qo'llanilgan)")
    
    # ----------------------------------------------------
    # VIZUALIZATSIYA QISMI (Endi 'df_final' dan foydalanadi)
    # ----------------------------------------------------

    # --- KPI ko'rsatkichlari ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Filtrdan so'ng jami", len(df_final))
    
    # Oxirgi yangilanish vaqti (Filtrsiz, chunki bu ma'lumot yuklangan vaqt)
    if '_submission_time' in df.columns:
        last_sub = df['_submission_time'].max().strftime('%Y-%m-%d %H:%M (Tashkent)')
        col2.metric("Oxirgi ma'lumot", last_sub)
    
    # --- Vizualizatsiya ---
    st.markdown("---")
    st.subheader("📈 Grafik tahlil")

    # Target ustunni tanlash (Endi u ham filtrdan keyin ishlaydi)
    target_col = st.selectbox(
        "Grafik uchun savolni tanlang:", 
        clean_columns,
        key='target_col'
    )

    if target_col and target_col in df_final.columns:
        chart_col1, chart_col2 = st.columns(2)
        
        # * Grafiklarga df_final o'tkaziladi *
        
        with chart_col1:
            st.write(f"**'{target_col}' bo'yicha taqsimot (Soni)**")
            counts = df_final[target_col].value_counts().reset_index()
            counts.columns = ['Javob', 'Soni']
            fig_bar = px.bar(counts, x='Javob', y='Soni', color='Javob', text='Soni')
            st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            st.write(f"**'{target_col}' bo'yicha taqsimot (Foiz)**")
            fig_pie = px.pie(counts, values='Soni', names='Javob', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
    # --- Jadval ko'rinishi va Yuklab olish tugmasi ---
    with st.expander("Jadvalni to'liq ko'rish (Filtrlangan Ma'lumot)"):
        st.dataframe(df_final)
        
    csv = df_final.to_csv(index=False).encode('utf-8')
    st.download_button(
        "CSV yuklab olish (Filtrlangan)", 
        csv, 
        "filtered_data.csv", 
        "text/csv"
    )

else:
    st.info("Iltimos, yon panelda 'Ma'lumotlarni yuklash' tugmasini bosing.")