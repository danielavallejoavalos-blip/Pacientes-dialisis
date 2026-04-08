import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import unicodedata

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Dashboard IMSS | Daniela Vallejo", layout="wide")

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
        'veracruz': 'Veracruz', 'yucatan': 'Yucatán', 'zacatecas': 'Zacatecas'
    }
    for key, value in base.items():
        if key in n: return value
    return "México" if 'mexico' in n else "DESCONOCIDO"

# --- 3. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    geo_data = requests.get("https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json").json()
    
    # Cargar Población
    df_pob = pd.read_excel("Poblacion mexico.xlsx", sheet_name='POBLACION POR ESTADO')
    df_pob['ESTADO_PADRE'] = df_pob['ESTADO'].apply(identificar_estado_padre)
    
    # Cargar Pacientes
    df_clin = pd.read_excel("TOTAL DE PACIENTES DP Y HD.xlsx", sheet_name='PACIENTES POR ESTADO')
    df_clin['ESTADO_PADRE'] = df_clin['ESTADO'].apply(identificar_estado_padre)
    
    return geo_data, df_pob, df_clin

# --- 4. INTERFAZ ---
try:
    geo_data, df_pob, df_clin = cargar_datos()
    
    st.title("🏥 Auditoría Clínica de Pacientes")
    st.sidebar.header("Opciones")
    
    tab1, tab2 = st.tabs(["🗺️ Mapa de Población", "📊 Datos Clínicos"])
    
    with tab1:
        st.subheader("Distribución Poblacional por Estado")
        fig = px.choropleth(
            df_pob, geojson=geo_data, locations='ESTADO_PADRE', 
            featureidkey="properties.name", color='POBLACIÓN',
            color_continuous_scale="Viridis", template="plotly_dark"
        )
        fig.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
    with tab2:
        st.subheader("Resumen de Pacientes por Estado")
        st.dataframe(df_clin)

except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.info("Asegúrate de que los archivos Excel están en el repositorio de GitHub.")
