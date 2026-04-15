import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import unicodedata

# --- 1. CONFIGURACIÓN E INYECCIÓN DE ESTILOS ---
st.set_page_config(page_title="IMSS Dashboard | Daniela Vallejo", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .fade-in {
        animation: fadeIn 0.6s;
        -webkit-animation: fadeIn 0.6s;
    }
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateX(20px); }
        100% { opacity: 1; transform: translateX(0); }
    }
    .report-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
        border-left: 5px solid #58a6ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. UTILIDADES DE NORMALIZACIÓN ---
def limpiar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def identificar_estado_padre(nombre_imss):
    n = limpiar_texto(nombre_imss)
    if any(x in n for x in ['mex. pte', 'mex. ote', 'oriente', 'poniente', 'edomex', 'estado de mexico']): return 'México'
    if any(x in n for x in ['cdmx', 'df', 'raza', 'siglo xxi', 'distrito federal', 'ciudad de mexico']): return 'Ciudad de México'
    if any(x in n for x in ['baja california sur']): return 'Baja California Sur'
    if any(x in n for x in ['baja california', 'norte']): return 'Baja California'
    if any(x in n for x in ['puebla', 'san jose']): return 'Puebla'
    if any(x in n for x in ['jalisco', 'occidente']): return 'Jalisco'
    
    base = {
        'aguascalientes': 'Aguascalientes', 'campeche': 'Campeche', 'chiapas': 'Chiapas', 
        'chihuahua': 'Chihuahua', 'colima': 'Colima', 'coahuila': 'Coahuila', 'durango': 'Durango', 
        'guanajuato': 'Guanajuato', 'guerrero': 'Guerrero', 'hidalgo': 'Hidalgo', 
        'michoacan': 'Michoacán', 'morelos': 'Morelos', 'nayarit': 'Nayarit', 'oaxaca': 'Oaxaca', 
        'nuevo leon': 'Nuevo León', 'queretaro': 'Querétaro', 'quintana roo': 'Quintana Roo', 
        'san luis potosi': 'San Luis Potosí', 'sinaloa': 'Sinaloa', 'sonora': 'Sonora', 
        'tabasco': 'Tabasco', 'tamaulipas': 'Tamaulipas', 'tlaxcala': 'Tlaxcala', 
        'veracruz': 'Veracruz', 'yucatan': 'Yucatán', 'zacatecas': 'Zacatecas'
    }
    for key, value in base.items():
        if key in n: return value
    if 'mexico' in n: return 'México'
    return "UNKNOWN"

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
    df_pob = df_pob[df_pob['ESTADO_PADRE'] != "UNKNOWN"]
    df_pob = df_pob.sort_values(by=['ESTADO_PADRE', 'AÑO'])
    df_pob['CREC_PCT'] = df_pob.groupby('ESTADO_PADRE')['POBLACIÓN'].pct_change().fillna(0) * 100
    df_pob['TENDENCIA'] = df_pob['CREC_PCT'].apply(lambda v: f"📈 +{v:.1f}%" if v > 0 else (f"📉 {v:.1f}%" if v < 0 else "➖ 0%"))
    
    df_clin = pd.read_excel("TOTAL DE PACIENTES DP Y HD.xlsx", sheet_name='PACIENTES POR ESTADO')
    df_clin.columns = df_clin.columns.astype(str).str.strip()
    col_pd, col_hd = 'DP TOTAL Dic, 2016', 'HD TOTAL Dic, 2016' # Mantengo nombres de columnas de Excel para evitar errores de lectura
    
    df_clin[col_pd] = pd.to_numeric(df_clin[col_pd].astype(str).str.replace(r'[ ,]', '', regex=True), errors='coerce').fillna(0)
    df_clin[col_hd] = pd.to_numeric(df_clin[col_hd].astype(str).str.replace(r'[ ,]', '', regex=True), errors='coerce').fillna(0)
    df_clin['TOTAL_PATIENTS'] = df_clin[col_pd] + df_clin[col_hd]
    df_clin['ESTADO_PADRE'] = df_clin['ESTADO'].apply(identificar_estado_padre)
    df_clin = df_clin[df_clin['ESTADO_PADRE'] != "UNKNOWN"]
    df_clin['TXT_DESGLOSE'] = "• " + df_clin['ESTADO'] + ": PD (" + df_clin[col_pd].astype(int).astype(str) + ") | HD (" + df_clin[col_hd].astype(int).astype(str) + ")"
    
    df_clin_agrupado = df_clin.groupby('ESTADO_PADRE').agg(
        TOTAL_PATIENTS=('TOTAL_PATIENTS', 'sum'),
        TOTAL_PD=(col_pd, 'sum'), TOTAL_HD=(col_hd, 'sum'),
        DESGLOSE=('TXT_DESGLOSE', lambda x: '<br>'.join(x))
    ).reset_index()

    datos_historicos = [
        {'AÑO': 2014, 'PD_APD': 15147, 'PD_CAPD': 18515, 'PD_TOTAL': 33662, 'PD_PCT': 57.98, 'HD_IN_CENTER': 10947, 'HD_OUTSOURCED': 13446, 'HD_TOTAL': 24393, 'HD_PCT': 42.02, 'TOTAL_PATIENTS': 58055},
        {'AÑO': 2015, 'PD_APD': 14695, 'PD_CAPD': 20036, 'PD_TOTAL': 34731, 'PD_PCT': 57.73, 'HD_IN_CENTER': 10706, 'HD_OUTSOURCED': 14725, 'HD_TOTAL': 25431, 'HD_PCT': 42.27, 'TOTAL_PATIENTS': 60162},
        {'AÑO': 2016, 'PD_APD': 14167, 'PD_CAPD': 22450, 'PD_TOTAL': 36617, 'PD_PCT': 56.75, 'HD_IN_CENTER': 10865, 'HD_OUTSOURCED': 17047, 'HD_TOTAL': 27912, 'HD_PCT': 43.25, 'TOTAL_PATIENTS': 64529},
        {'AÑO': 2017, 'PD_APD': 14753, 'PD_CAPD': 23941, 'PD_TOTAL': 38694, 'PD_PCT': 55.96, 'HD_IN_CENTER': 11485, 'HD_OUTSOURCED': 18972, 'HD_TOTAL': 30457, 'HD_PCT': 44.04, 'TOTAL_PATIENTS': 69151},
        {'AÑO': 2018, 'PD_APD': 15846, 'PD_CAPD': 25438, 'PD_TOTAL': 41284, 'PD_PCT': 55.38, 'HD_IN_CENTER': 11865, 'HD_OUTSOURCED': 21394, 'HD_TOTAL': 33259, 'HD_PCT': 44.62, 'TOTAL_PATIENTS': 74543},
        {'AÑO': 2019, 'PD_APD': 15267, 'PD_CAPD': 23666, 'PD_TOTAL': 38933, 'PD_PCT': 54.46, 'HD_IN_CENTER': 10464, 'HD_OUTSOURCED': 22091, 'HD_TOTAL': 32555, 'HD_PCT': 45.54, 'TOTAL_PATIENTS': 71488},
        {'AÑO': 2020, 'PD_APD': 15953, 'PD_CAPD': 25983, 'PD_TOTAL': 41936, 'PD_PCT': 54.44, 'HD_IN_CENTER': 11347, 'HD_OUTSOURCED': 23752, 'HD_TOTAL': 35099, 'HD_PCT': 45.56, 'TOTAL_PATIENTS': 77035},
        {'AÑO': 2021, 'PD_APD': 13030, 'PD_CAPD': 20948, 'PD_TOTAL': 33978, 'PD_PCT': 50.45, 'HD_IN_CENTER': 10926, 'HD_OUTSOURCED': 22445, 'HD_TOTAL': 33371, 'HD_PCT': 49.55, 'TOTAL_PATIENTS': 67349},
        {'AÑO': 2022, 'PD_APD': 12415, 'PD_CAPD': 21327, 'PD_TOTAL': 33742, 'PD_PCT': 48.19, 'HD_IN_CENTER': 12062, 'HD_OUTSOURCED': 24219, 'HD_TOTAL': 36281, 'HD_PCT': 51.81, 'TOTAL_PATIENTS': 70023},
        {'AÑO': 2023, 'PD_APD': 14663, 'PD_CAPD': 21411, 'PD_TOTAL': 36074, 'PD_PCT': 46.44, 'HD_IN_CENTER': 12691, 'HD_OUTSOURCED': 28922, 'HD_TOTAL': 41613, 'HD_PCT': 53.56, 'TOTAL_PATIENTS': 77687},
        {'AÑO': 2024, 'PD_APD': 16554, 'PD_CAPD': 21233, 'PD_TOTAL': 37787, 'PD_PCT': 45.14, 'HD_IN_CENTER': 14461, 'HD_OUTSOURCED': 31456, 'HD_TOTAL': 45917, 'HD_PCT': 54.86, 'TOTAL_PATIENTS': 83704},
        {'AÑO': 2025, 'PD_APD': 17019, 'PD_CAPD': 19579, 'PD_TOTAL': 36598, 'PD_PCT': 43.84, 'HD_IN_CENTER': 13427, 'HD_OUTSOURCED': 33465, 'HD_TOTAL': 46892, 'HD_PCT': 56.16, 'TOTAL_PATIENTS': 83490},
        {'AÑO': 2026, 'PD_APD': 17107, 'PD_CAPD': 19432, 'PD_TOTAL': 36539, 'PD_PCT': 43.22, 'HD_IN_CENTER': 13765, 'HD_OUTSOURCED': 34246, 'HD_TOTAL': 48011, 'HD_PCT': 56.78, 'TOTAL_PATIENTS': 84550}
    ]
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
    st.markdown("*Use the **▶ Play** button below the map to see the animated historical evolution.*")
    
    ultimo_anio = df_poblacion['AÑO'].max()
    df_ultimo = df_poblacion[df_poblacion['AÑO'] == ultimo_anio]
    col1, col2 = st.columns(2)
    col1.metric(f"Total National Population ({ultimo_anio})", f"{df_ultimo['POBLACIÓN'].sum():,.0f}")
    estado_top = df_ultimo.sort_values('POBLACIÓN', ascending=False).iloc[0]
    col2.metric(f"State with Highest Burden ({ultimo_anio})", estado_top['ESTADO_PADRE'], f"{estado_top['POBLACIÓN']:,.0f}")
    
    fig = px.choropleth(
        df_poblacion, geojson=geo_data, locations='ESTADO_PADRE', featureidkey="properties.name",
        color='POBLACIÓN', animation_frame='AÑO', color_continuous_scale="Greens",
        range_color=[0, df_poblacion['POBLACIÓN'].max()], custom_data=['TENDENCIA']
    )
    fig.update_traces(
        hovertemplate="<b>%{location}</b><br>Patients: %{z:,.0f}<br>Trend: %{customdata[0]}<extra></extra>",
        marker_line_color='#333333',
        marker_line_width=0.8
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=650, template="plotly_white", paper_bgcolor="white", geo_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

elif modulo_seleccionado == "🏥 Treatment Landscape in Mexico": 
    st.header("Treatment Landscape in Mexico")
    
    tab1, tab2 = st.tabs(["📈 1. National Historical Report", "🗺️ 2. Geographic Distribution (2016 Snapshot)"])
    
    with tab1:
        st.subheader("National Evolution: PD and HD")
        anios_disponibles = sorted(df_historico_clinico['AÑO'].unique().tolist())
        anio_sel = st.select_slider("🗓️ Select Year to View:", options=anios_disponibles, value=2026)
        data_anio = df_historico_clinico[df_historico_clinico['AÑO'] == anio_sel].iloc[0]
