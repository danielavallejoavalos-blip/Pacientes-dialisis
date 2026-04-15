import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import unicodedata

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="IMSS Dashboard | Daniela Vallejo", layout="wide")

# Estilos CSS para las tarjetas y animaciones
st.markdown("""
    <style>
    .report-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
        border-left: 5px solid #58a6ff;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE APOYO ---
def limpiar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def identificar_estado_padre(nombre_imss):
    n = limpiar_texto(nombre_imss)
    if any(x in n for x in ['mex. pte', 'mex. ote', 'oriente', 'poniente', 'edomex', 'estado de mexico']): return 'México'
    if any(x in n for x in ['cdmx', 'df', 'raza', 'siglo xxi', 'distrito federal', 'ciudad de mexico']): return 'Ciudad de México'
    
    base = {
        'aguascalientes': 'Aguascalientes', 'campeche': 'Campeche', 'chiapas': 'Chiapas', 
        'chihuahua': 'Chihuahua', 'colima': 'Colima', 'coahuila': 'Coahuila', 'durango': 'Durango', 
        'guanajuato': 'Guanajuato', 'guerrero': 'Guerrero', 'hidalgo': 'Hidalgo', 
        'michoacan': 'Michoacán', 'morelos': 'Morelos', 'nayarit': 'Nayarit', 'oaxaca': 'Oaxaca', 
        'nuevo leon': 'Nuevo León', 'queretaro': 'Querétaro', 'quintana roo': 'Quintana Roo', 
        'san luis potosi': 'San Luis Potosí', 'sinaloa': 'Sinaloa', 'sonora': 'Sonora', 
        'tabasco': 'Tabasco', 'tamaulipas': 'Tamaulipas', 'tlaxcala': 'Tlaxcala', 
        'veracruz': 'Veracruz', 'yucatan': 'Yucatán', 'zacatecas': 'Zacatecas',
        'baja california sur': 'Baja California Sur', 'baja california': 'Baja California',
        'puebla': 'Puebla', 'jalisco': 'Jalisco'
    }
    for key, value in base.items():
        if key in n: return value
    return "UNKNOWN"

# --- 3. MOTOR DE DATOS (ETL) ---
@st.cache_data
def cargar_todo():
    # GeoJSON para el mapa
    geo_data = requests.get("https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json").json()
    
    # Datos de Población
    df_pob = pd.read_excel("Poblacion mexico.xlsx", sheet_name='POBLACION POR ESTADO')
    df_pob['AÑO'] = df_pob['AÑO'].ffill().astype(int)
    df_pob['POBLACIÓN'] = pd.to_numeric(df_pob['POBLACIÓN'].astype(str).str.replace(r'[ ,]', '', regex=True), errors='coerce').fillna(0)
    df_pob['ESTADO_PADRE'] = df_pob['ESTADO'].apply(identificar_estado_padre)
    
    # Datos Clínicos (Snapshot 2016)
    df_clin = pd.read_excel("TOTAL DE PACIENTES DP Y HD.xlsx", sheet_name='PACIENTES POR ESTADO')
    df_clin.columns = df_clin.columns.astype(str).str.strip()
    
    # Mapeo de columnas del Excel (DP -> PD)
    col_dp_excel = 'DP TOTAL Dic, 2016'
    col_hd_excel = 'HD TOTAL Dic, 2016'
    
    df_clin['TOTAL_PD'] = pd.to_numeric(df_clin[col_dp_excel].astype(str).str.replace(r'[ ,]', '', regex=True), errors='coerce').fillna(0)
    df_clin['TOTAL_HD'] = pd.to_numeric(df_clin[col_hd_excel].astype(str).str.replace(r'[ ,]', '', regex=True), errors='coerce').fillna(0)
    df_clin['TOTAL_PATIENTS'] = df_clin['TOTAL_PD'] + df_clin['TOTAL_HD']
    df_clin['ESTADO_PADRE'] = df_clin['ESTADO'].apply(identificar_estado_padre)
    
    df_clin_resumen = df_clin.groupby('ESTADO_PADRE').agg(
        TOTAL_PATIENTS=('TOTAL_PATIENTS', 'sum'),
        TOTAL_PD=('TOTAL_PD', 'sum'),
        TOTAL_HD=('TOTAL_HD', 'sum')
    ).reset_index()

    # Historial Nacional Traducido
    hist_data = [
        {'AÑO': 2014, 'PD_APD': 15147, 'PD_CAPD': 18515, 'PD_TOTAL': 33662, 'PD_PCT': 58, 'HD_IN_CENTER': 10947, 'HD_OUTSOURCED': 13446, 'HD_TOTAL': 24393, 'HD_PCT': 42, 'TOTAL_PATIENTS': 58055},
        {'AÑO': 2015, 'PD_APD': 14695, 'PD_CAPD': 20036, 'PD_TOTAL': 34731, 'PD_PCT': 57, 'HD_IN_CENTER': 10706, 'HD_OUTSOURCED': 14725, 'HD_TOTAL': 25431, 'HD_PCT': 43, 'TOTAL_PATIENTS': 60162},
        {'AÑO': 2016, 'PD_APD': 14167, 'PD_CAPD': 22450, 'PD_TOTAL': 36617, 'PD_PCT': 56, 'HD_IN_CENTER': 10865, 'HD_OUTSOURCED': 17047, 'HD_TOTAL': 27912, 'HD_PCT': 44, 'TOTAL_PATIENTS': 64529},
        {'AÑO': 2017, 'PD_APD': 14753, 'PD_CAPD': 23941, 'PD_TOTAL': 38694, 'PD_PCT': 56, 'HD_IN_CENTER': 11485, 'HD_OUTSOURCED': 18972, 'HD_TOTAL': 30457, 'HD_PCT': 44, 'TOTAL_PATIENTS': 69151},
        {'AÑO': 2018, 'PD_APD': 15846, 'PD_CAPD': 25438, 'PD_TOTAL': 41284, 'PD_PCT': 55, 'HD_IN_CENTER': 11865, 'HD_OUTSOURCED': 21394, 'HD_TOTAL': 33259, 'HD_PCT': 45, 'TOTAL_PATIENTS': 74543},
        {'AÑO': 2019, 'PD_APD': 15267, 'PD_CAPD': 23666, 'PD_TOTAL': 38933, 'PD_PCT': 54, 'HD_IN_CENTER': 10464, 'HD_OUTSOURCED': 22091, 'HD_TOTAL': 32555, 'HD_PCT': 46, 'TOTAL_PATIENTS': 71488},
        {'AÑO': 2020, 'PD_APD': 15953, 'PD_CAPD': 25983, 'PD_TOTAL': 41936, 'PD_PCT': 54, 'HD_IN_CENTER': 11347, 'HD_OUTSOURCED': 23752, 'HD_TOTAL': 35099, 'HD_PCT': 46, 'TOTAL_PATIENTS': 77035},
        {'AÑO': 2021, 'PD_APD': 13030, 'PD_CAPD': 20948, 'PD_TOTAL': 33978, 'PD_PCT': 50, 'HD_IN_CENTER': 10926, 'HD_OUTSOURCED': 22445, 'HD_TOTAL': 33371, 'HD_PCT': 50, 'TOTAL_PATIENTS': 67349},
        {'AÑO': 2022, 'PD_APD': 12415, 'PD_CAPD': 21327, 'PD_TOTAL': 33742, 'PD_PCT': 48, 'HD_IN_CENTER': 12062, 'HD_OUTSOURCED': 24219, 'HD_TOTAL': 36281, 'HD_PCT': 52, 'TOTAL_PATIENTS': 70023},
        {'AÑO': 2023, 'PD_APD': 14663, 'PD_CAPD': 21411, 'PD_TOTAL': 36074, 'PD_PCT': 46, 'HD_IN_CENTER': 12691, 'HD_OUTSOURCED': 28922, 'HD_TOTAL': 41613, 'HD_PCT': 54, 'TOTAL_PATIENTS': 77687},
        {'AÑO': 2024, 'PD_APD': 16554, 'PD_CAPD': 21233, 'PD_TOTAL': 37787, 'PD_PCT': 45, 'HD_IN_CENTER': 14461, 'HD_OUTSOURCED': 31456, 'HD_TOTAL': 45917, 'HD_PCT': 55, 'TOTAL_PATIENTS': 83704},
        {'AÑO': 2025, 'PD_APD': 17019, 'PD_CAPD': 19579, 'PD_TOTAL': 36598, 'PD_PCT': 44, 'HD_IN_CENTER': 13427, 'HD_OUTSOURCED': 33465, 'HD_TOTAL': 46892, 'HD_PCT': 56, 'TOTAL_PATIENTS': 83490},
        {'AÑO': 2026, 'PD_APD': 17107, 'PD_CAPD': 19432, 'PD_TOTAL': 36539, 'PD_PCT': 43, 'HD_IN_CENTER': 13765, 'HD_OUTSOURCED': 34246, 'HD_TOTAL': 48011, 'HD_PCT': 57, 'TOTAL_PATIENTS': 84550}
    ]
    df_hist = pd.DataFrame(hist_data)
    
    return geo_data, df_pob, df_clin_resumen, df_hist

# --- 4. INICIO DE APP ---
try:
    geo, df_p, df_c, df_h = cargar_todo()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 5. INTERFAZ ---
st.sidebar.title("PATIENT DASHBOARD")
view = st.sidebar.radio("Navigation:", ["Demographics", "Treatments"])

if view == "Demographics":
    st.header("Demographic Density")
    fig = px.choropleth(df_p, geojson=geo, locations='ESTADO_PADRE', featureidkey="properties.name",
                        color='POBLACIÓN', animation_frame='AÑO', color_continuous_scale="Greens", template="plotly_white")
    fig.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.header("Treatment Landscape")
    t1, t2 = st.tabs(["National Trends", "Regional View"])
    
    with t1:
        year = st.select_slider("Select Year:", options=sorted(df_h['AÑO'].unique()), value=2026)
        row = df_h[df_h['AÑO'] == year].iloc[0]
        
        st.metric("Total Patients", f"{row['TOTAL_PATIENTS']:,}")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"🔵 PD ({row['PD_PCT']}%)")
            st.write(f"**Total PD:** {row['PD_TOTAL']:,}")
            st.write(f"- APD: {row['PD_APD']:,}")
            st.write(f"- CAPD: {row['PD_CAPD']:,}")
        with c2:
            st.subheader(f"🔴 HD ({row['HD_PCT']}%)")
            st.write(f"**Total HD:** {row['HD_TOTAL']:,}")
            st.write(f"- In-Center: {row['HD_IN_CENTER']:,}")
            st.write(f"- Outsourced: {row['HD_OUTSOURCED']:,}")
            
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=df_h['AÑO'], y=df_h['PD_TOTAL'], name="PD", line=dict(color='#3498db')))
        fig_line.add_trace(go.Scatter(x=df_h['AÑO'], y=df_h['HD_TOTAL'], name="HD", line=dict(color='#e74c3c')))
        fig_line.update_layout(template="plotly_white", height=300)
        st.plotly_chart(fig_line, use_container_width=True)

    with t2:
        st.subheader("Regional Snapshot (2016)")
        fig_map = px.choropleth(df_c, geojson=geo, locations='ESTADO_PADRE', featureidkey="properties.name",
                                color='TOTAL_PATIENTS', color_continuous_scale="Viridis", template="plotly_white")
        fig_map.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig_map, use_container_width=True)
