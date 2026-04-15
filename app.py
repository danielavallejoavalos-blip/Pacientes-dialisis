import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import unicodedata

# --- CONFIGURACIÓN ---
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

# --- UTILIDADES ---
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

# --- SESSION STATE ---
if 'selected_state' not in st.session_state:
    st.session_state.selected_state = None

# --- CARGA DE DATOS ---
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
    
    df_clin['TXT_DESGLOSE'] = "• " + df_clin['ESTADO'] + ": PD (" + df_clin[col_dp].astype(int).astype(str) + ") | HD (" + df_clin[col_hd].astype(int).astype(str) + ")"

    df_clin_agrupado = df_clin.groupby('ESTADO_PADRE').agg(
        TOTAL_PACIENTES=('TOTAL_PACIENTES', 'sum'),
        TOTAL_DP=('DP TOTAL Dic, 2016', 'sum'),
        TOTAL_HD=('HD TOTAL Dic, 2016', 'sum'),
        DESGLOSE=('TXT_DESGLOSE', lambda x: '<br>'.join(x))
    ).reset_index()

    datos_historicos = [ ... ]  # (mantengo el mismo diccionario completo que te di antes)

    df_hist_clin = pd.DataFrame(datos_historicos)
    return geo_data, df_pob, df_clin_agrupado, df_hist_clin

try:
    geo_data, df_poblacion, df_clinico, df_historico_clinico = cargar_datos_maestros()
except Exception as e:
    st.error(f"Missing Excel files. Error: {e}")
    st.stop()

# --- SIDEBAR ---
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

# ====================== MAPA ANIMADO ======================
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
        df_poblacion,
        geojson=geo_data,
        locations='ESTADO_PADRE',
        featureidkey="properties.name",
        color='POBLACIÓN',
        animation_frame='AÑO',
        color_continuous_scale="Greens",
        range_color=[0, df_poblacion['POBLACIÓN'].max()],
        custom_data=['TENDENCIA']
    )

    fig.update_traces(
        hovertemplate="<b>%{location}</b><br>Population: %{z:,.0f}<br>Trend: %{customdata[0]}<extra></extra>",
        marker_line_color='#333333',
        marker_line_width=0.8
    )

    # === CONFIGURACIÓN CLAVE PARA QUE SOLO SE VEA MÉXICO ===
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=True,
        coastlinecolor="#444444",
        showland=True,
        landcolor="#f8f9fa",
        projection_type="mercator",      # Mejor proyección para México
        center={"lat": 23.5, "lon": -102},  # Centro de México
        projection_scale=4.5             # Zoom inicial (ajusta si quieres más cerca o lejos)
    )

    fig.update_layout(
        margin={"r":0, "t":30, "l":0, "b":0},
        height=650,
        template="plotly",
        paper_bgcolor="white",
        geo_bgcolor="#f8f9fa",
        title=None
    )

    st.plotly_chart(fig, use_container_width=True)

# ====================== TREATMENT LANDSCAPE ======================
else:
    st.header("Treatment Landscape in Mexico")
    tab1, tab2 = st.tabs(["📈 1. National Historical Report", "🗺️ 2. Geographic Distribution (2016 Snapshot)"])
    
    with tab1:
        # ... (mismo código de la pestaña 1 que te di antes - sin cambios)

    with tab2:
        st.subheader("Treatment Landscape in Mexico")
        col_map, col_dash = st.columns([1.8, 1])
        
        with col_map:
            capa = st.radio("View Layer:", ["Renal Replacement Therapy 2026", "PD (2016)", "HD (2016)"], horizontal=True)
            
            map_config = {
                "Renal Replacement Therapy 2026": ('TOTAL_PACIENTES', 'Greens'),
                "PD (2016)": ('TOTAL_DP', 'Blues'),
                "HD (2016)": ('TOTAL_HD', 'Reds')
            }
            val_col, scale = map_config[capa]

            fig_audit = go.Figure(go.Choropleth(
                geojson=geo_data,
                locations=df_clinico['ESTADO_PADRE'],
                z=df_clinico[val_col],
                featureidkey="properties.name",
                colorscale=scale,
                marker_line_color='#333333',
                marker_line_width=0.8
            ))

            # === MISMA CONFIGURACIÓN PARA QUE SOLO SE VEA MÉXICO ===
            fig_audit.update_geos(
                fitbounds="locations",
                visible=False,
                showcoastlines=True,
                coastlinecolor="#444444",
                showland=True,
                landcolor="#f8f9fa",
                projection_type="mercator",
                center={"lat": 23.5, "lon": -102},
                projection_scale=4.5
            )

            fig_audit.update_layout(
                template="plotly",
                paper_bgcolor="white",
                geo_bgcolor="#f8f9fa",
                margin={"r":0,"t":0,"l":0,"b":0},
                height=600,
                clickmode="event+select",
                dragmode=False
            )

            map_event = st.plotly_chart(fig_audit, use_container_width=True, on_select="rerun", selection_mode="points", key="audit_map")

            if map_event and "selection" in map_event and map_event["selection"]["points"]:
                st.session_state.selected_state = map_event["selection"]["points"][0]["location"]

        with col_dash:
            if st.session_state.selected_state:
                # ... (el resto del código de la tarjeta y mini-mapa se mantiene igual)
                pass
            else:
                st.info("Select a state on the map to view the detailed breakdown.")
