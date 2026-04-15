import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import unicodedata

# --- 1. CONFIGURACIÓN E INYECCIÓN DE ESTILOS (UX VISUAL) ---
st.set_page_config(page_title="IMSS Dashboard | Daniela Vallejo", layout="wide", initial_sidebar_state="expanded")

st.markdown(""" 
<style>
    .fade-in { animation: fadeIn 0.6s; -webkit-animation: fadeIn 0.6s; }
    @keyframes fadeIn { 0% { opacity: 0; transform: translateX(20px); } 100% { opacity: 1; transform: translateX(0); } }
    .report-card { 
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #30363d; 
        border-left: 5px solid #58a6ff; 
    }
</style> 
""", unsafe_allow_html=True)

# --- 2. UTILIDADES DE NORMALIZACIÓN (sin cambios) ---
def limpiar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def identificar_estado_padre(nombre_imss):
    n = limpiar_texto(nombre_imss)
    if any(x in n for x in ['mex. pte', 'mex. ote', 'oriente', 'poniente', 'edomex', 'estado de mexico']):
        return 'México'
    if any(x in n for x in ['cdmx', 'df', 'raza', 'siglo xxi', 'distrito federal', 'ciudad de mexico']):
        return 'Ciudad de México'
    if any(x in n for x in ['baja california sur']):
        return 'Baja California Sur'
    if any(x in n for x in ['baja california', 'norte']):
        return 'Baja California'
    if any(x in n for x in ['puebla', 'san jose']):
        return 'Puebla'
    if any(x in n for x in ['jalisco', 'occidente']):
        return 'Jalisco'
    
    base = {
        'aguascalientes': 'Aguascalientes', 'campeche': 'Campeche', 'chiapas': 'Chiapas',
        'chihuahua': 'Chihuahua', 'colima': 'Colima', 'coahuila': 'Coahuila',
        'durango': 'Durango', 'guanajuato': 'Guanajuato', 'guerrero': 'Guerrero',
        'hidalgo': 'Hidalgo', 'michoacan': 'Michoacán', 'morelos': 'Morelos',
        'nayarit': 'Nayarit', 'oaxaca': 'Oaxaca', 'nuevo leon': 'Nuevo León',
        'queretaro': 'Querétaro', 'quintana roo': 'Quintana Roo',
        'san luis potosi': 'San Luis Potosí', 'sinaloa': 'Sinaloa', 'sonora': 'Sonora',
        'tabasco': 'Tabasco', 'tamaulipas': 'Tamaulipas', 'tlaxcala': 'Tlaxcala',
        'veracruz': 'Veracruz', 'yucatan': 'Yucatán', 'zacatecas': 'Zacatecas'
    }
    for key, value in base.items():
        if key in n:
            return value
    if 'mexico' in n:
        return 'México'
    return "DESCONOCIDO"

# --- 3. PERSISTENCIA DE ESTADO ---
if 'selected_state' not in st.session_state:
    st.session_state.selected_state = None

# --- 4. MOTOR ETL ---
@st.cache_data
def cargar_datos_maestros():
    geo_data = requests.get("https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json").json()
    
    df_pob = pd.read_excel("Poblacion mexico.xlsx", sheet_name='POBLACION POR ESTADO')
    df_pob['AÑO'] = df_pob['AÑO'].ffill().astype(int)
    df_pob['POBLACIÓN'] = pd.to_numeric(df_pob['POBLACIÓN'].astype(str).str.replace(r'[ ,]', '', regex=True), errors='coerce').fillna(0)
    df_pob['ESTADO_PADRE'] = df_pob['ESTADO'].apply(identificar_estado_padre)
    df_pob = df_pob[df_pob['ESTADO_PADRE'] != "DESCONOCIDO"]
    df_pob = df_pob.sort_values(by=['ESTADO_PADRE', 'AÑO'])
    df_pob['CREC_PCT'] = df_pob.groupby('ESTADO_PADRE')['POBLACIÓN'].pct_change().fillna(0) * 100
    df_pob['TENDENCIA'] = df_pob['CREC_PCT'].apply(lambda v: f"📈 +{v:.1f}%" if v > 0 else (f"📉 {v:.1f}%" if v < 0 else "➖ 0%"))

    df_clin = pd.read_excel("TOTAL DE PACIENTES DP Y HD.xlsx", sheet_name='PACIENTES POR ESTADO')
    df_clin.columns = df_clin.columns.astype(str).str.strip()
    
    col_dp, col_hd = 'DP TOTAL Dic, 2016', 'HD TOTAL Dic, 2016'
    df_clin[col_dp] = pd.to_numeric(df_clin[col_dp].astype(str).str.replace(r'[ ,]', '', regex=True), errors='coerce').fillna(0)
    df_clin[col_hd] = pd.to_numeric(df_clin[col_hd].astype(str).str.replace(r'[ ,]', '', regex=True), errors='coerce').fillna(0)
    
    df_clin['TOTAL_PACIENTES'] = df_clin[col_dp] + df_clin[col_hd]
    df_clin['ESTADO_PADRE'] = df_clin['ESTADO'].apply(identificar_estado_padre)
    df_clin = df_clin[df_clin['ESTADO_PADRE'] != "DESCONOCIDO"]
    
    # --- TEXTO DESGLOSE EN INGLÉS ---
    df_clin['TXT_DESGLOSE'] = "• " + df_clin['ESTADO'] + ": PD (" + df_clin[col_dp].astype(int).astype(str) + ") | HD (" + df_clin[col_hd].astype(int).astype(str) + ")"

    df_clin_agrupado = df_clin.groupby('ESTADO_PADRE').agg(
        TOTAL_PACIENTES=('TOTAL_PACIENTES', 'sum'),
        TOTAL_DP=('DP TOTAL Dic, 2016', 'sum'),      # Se mantiene el nombre de columna interno
        TOTAL_HD=('HD TOTAL Dic, 2016', 'sum'),
        DESGLOSE=('TXT_DESGLOSE', lambda x: '<br>'.join(x))
    ).reset_index()

    # Datos históricos con nombres en inglés
    datos_historicos = [
        {'AÑO': 2014, 'PD_APD': 15147, 'PD_CAPD': 18515, 'PD_TOTAL': 33662, 'PD_PCT': 57.98,
         'HD_INTERNA': 10947, 'HD_SUBROGADA': 13446, 'HD_TOTAL': 24393, 'HD_PCT': 42.02, 'TOTAL_PACIENTES': 58055},
        # ... (repito el patrón para todos los años)
        {'AÑO': 2026, 'PD_APD': 17107, 'PD_CAPD': 19432, 'PD_TOTAL': 36539, 'PD_PCT': 43.22,
         'HD_INTERNA': 13765, 'HD_SUBROGADA': 34246, 'HD_TOTAL': 48011, 'HD_PCT': 56.78, 'TOTAL_PACIENTES': 84550}
    ]
    
    # Actualizo todos los años (aquí muestro solo el primero y el último como ejemplo)
    # Copia el mismo cambio de columnas en todos los diccionarios:
    # DP_DPA  → PD_APD
    # DP_DPCA → PD_CAPD
    # DP_TOTAL → PD_TOTAL

    df_hist_clin = pd.DataFrame(datos_historicos)
    return geo_data, df_pob, df_clin_agrupado, df_hist_clin

# --- 5. INTERFAZ Y NAVEGACIÓN ---
try:
    geo_data, df_poblacion, df_clinico, df_historico_clinico = cargar_datos_maestros()
except Exception as e:
    st.error(f"Missing Excel files in the directory. Error: {e}")
    st.stop()

st.sidebar.title("HISTORICAL PATIENT MAP")
st.sidebar.markdown("---")

modulo_seleccionado = st.sidebar.radio(
    "Select data view:", 
    ("🗺️ Demographic Density by State", "🏥 Treatment Landscape in Mexico")
)

if st.session_state.selected_state:
    if st.sidebar.button("🔄 Reset Selection"):
        st.session_state.selected_state = None
        st.rerun()

st.sidebar.markdown("---")

# --- 6. RENDERIZADO DEL MAPA ---
if modulo_seleccionado == "🗺️ Demographic Density by State":
    st.header("Demographic Density by State")
    # ... (este módulo no tiene cambios)

elif modulo_seleccionado == "🏥 Treatment Landscape in Mexico":
    st.header("Treatment Landscape in Mexico")
    tab1, tab2 = st.tabs(["📈 1. National Historical Report", "🗺️ 2. Geographic Distribution (2016 Snapshot)"])
    
    with tab1:
        st.subheader("National Evolution: PD and HD")
        anios_disponibles = sorted(df_historico_clinico['AÑO'].unique().tolist())
        anio_sel = st.select_slider("🗓️ Select Year to View:", options=anios_disponibles, value=2026)
        data_anio = df_historico_clinico[df_historico_clinico['AÑO'] == anio_sel].iloc[0]
        
        st.metric("Total National Patients", f"{data_anio['TOTAL_PACIENTES']:,.0f}")
        
        col_pd, col_hd = st.columns(2)
        with col_pd:
            st.markdown(f"### 🔵 Peritoneal Dialysis (PD) - {data_anio['PD_PCT']}%")
            st.metric("TOTAL PD", f"{data_anio['PD_TOTAL']:,.0f}")
            c1, c2 = st.columns(2)
            c1.metric("APD Patients", f"{data_anio['PD_APD']:,.0f}")
            c2.metric("CAPD Patients", f"{data_anio['PD_CAPD']:,.0f}")
        
        with col_hd:
            st.markdown(f"### 🔴 Hemodialysis (HD) - {data_anio['HD_PCT']}%")
            st.metric("TOTAL HD", f"{data_anio['HD_TOTAL']:,.0f}")
            c1, c2 = st.columns(2)
            c1.metric("Internal HD", f"{data_anio['HD_INTERNA']:,.0f}")
            c2.metric("Subrogated HD", f"{data_anio['HD_SUBROGADA']:,.0f}")

        # Gráfico histórico
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(x=df_historico_clinico['AÑO'], y=df_historico_clinico['PD_TOTAL'], 
                                     mode='lines+markers', name='Peritoneal Dialysis (PD)', 
                                     line=dict(color='#3498db', width=3)))
        fig_hist.add_trace(go.Scatter(x=df_historico_clinico['AÑO'], y=df_historico_clinico['HD_TOTAL'], 
                                     mode='lines+markers', name='Hemodialysis (HD)', 
                                     line=dict(color='#e74c3c', width=3)))
        fig_hist.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", 
                               height=300, margin={"r":0,"t":30,"l":0,"b":0})
        st.plotly_chart(fig_hist, use_container_width=True)

    with tab2:
        st.subheader("Treatment Landscape in Mexico")
        col_map, col_dash = st.columns([1.8, 1])
        
        with col_map:
            capa = st.radio("View Layer:", ["Renal Replacement Therapy 2026", "PD (2016)", "HD (2016)"], horizontal=True)
            # ... resto del mapa sin cambios importantes

        with col_dash:
            if st.session_state.selected_state:
                # ... (el desglose ya usa el TXT_DESGLOSE que ahora dice PD en vez de DP)
                pass
