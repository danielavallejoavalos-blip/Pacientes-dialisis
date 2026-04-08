import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import unicodedata

# --- 1. CONFIGURACIÓN E INYECCIÓN DE ESTILOS (UX VISUAL) ---
st.set_page_config(page_title="Dashboard IMSS | Daniela Vallejo", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Animación de entrada para el panel lateral */
    .fade-in {
        animation: fadeIn 0.6s;
        -webkit-animation: fadeIn 0.6s;
    }
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateX(20px); }
        100% { opacity: 1; transform: translateX(0); }
    }
    /* Estilo de tarjeta para el desglose */
    .report-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
        border-left: 5px solid #58a6ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. UTILIDADES DE NORMALIZACIÓN (TU CEREBRO INTACTO) ---
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
    return "DESCONOCIDO"

# --- 3. PERSISTENCIA DE ESTADO (SESSION STATE) ---
if 'selected_state' not in st.session_state:
    st.session_state.selected_state = None

# --- 4. MOTOR ETL (TUS DATOS INTACTOS) ---
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
    df_clin['TXT_DESGLOSE'] = "• " + df_clin['ESTADO'] + ": DP (" + df_clin[col_dp].astype(int).astype(str) + ") | HD (" + df_clin[col_hd].astype(int).astype(str) + ")"
    
    df_clin_agrupado = df_clin.groupby('ESTADO_PADRE').agg(
        TOTAL_PACIENTES=('TOTAL_PACIENTES', 'sum'),
        TOTAL_DP=(col_dp, 'sum'), TOTAL_HD=(col_hd, 'sum'),
        DESGLOSE=('TXT_DESGLOSE', lambda x: '<br>'.join(x))
    ).reset_index()

    datos_historicos = [
        {'AÑO': 2014, 'DP_DPA': 15147, 'DP_DPCA': 18515, 'DP_TOTAL': 33662, 'DP_PCT': 57.98, 'HD_INTERNA': 10947, 'HD_SUBROGADA': 13446, 'HD_TOTAL': 24393, 'HD_PCT': 42.02, 'TOTAL_PACIENTES': 58055},
        {'AÑO': 2015, 'DP_DPA': 14695, 'DP_DPCA': 20036, 'DP_TOTAL': 34731, 'DP_PCT': 57.73, 'HD_INTERNA': 10706, 'HD_SUBROGADA': 14725, 'HD_TOTAL': 25431, 'HD_PCT': 42.27, 'TOTAL_PACIENTES': 60162},
        {'AÑO': 2016, 'DP_DPA': 14167, 'DP_DPCA': 22450, 'DP_TOTAL': 36617, 'DP_PCT': 56.75, 'HD_INTERNA': 10865, 'HD_SUBROGADA': 17047, 'HD_TOTAL': 27912, 'HD_PCT': 43.25, 'TOTAL_PACIENTES': 64529},
        {'AÑO': 2017, 'DP_DPA': 14753, 'DP_DPCA': 23941, 'DP_TOTAL': 38694, 'DP_PCT': 55.96, 'HD_INTERNA': 11485, 'HD_SUBROGADA': 18972, 'HD_TOTAL': 30457, 'HD_PCT': 44.04, 'TOTAL_PACIENTES': 69151},
        {'AÑO': 2018, 'DP_DPA': 15846, 'DP_DPCA': 25438, 'DP_TOTAL': 41284, 'DP_PCT': 55.38, 'HD_INTERNA': 11865, 'HD_SUBROGADA': 21394, 'HD_TOTAL': 33259, 'HD_PCT': 44.62, 'TOTAL_PACIENTES': 74543},
        {'AÑO': 2019, 'DP_DPA': 15267, 'DP_DPCA': 23666, 'DP_TOTAL': 38933, 'DP_PCT': 54.46, 'HD_INTERNA': 10464, 'HD_SUBROGADA': 22091, 'HD_TOTAL': 32555, 'HD_PCT': 45.54, 'TOTAL_PACIENTES': 71488},
        {'AÑO': 2020, 'DP_DPA': 15953, 'DP_DPCA': 25983, 'DP_TOTAL': 41936, 'DP_PCT': 54.44, 'HD_INTERNA': 11347, 'HD_SUBROGADA': 23752, 'HD_TOTAL': 35099, 'HD_PCT': 45.56, 'TOTAL_PACIENTES': 77035},
        {'AÑO': 2021, 'DP_DPA': 13030, 'DP_DPCA': 20948, 'DP_TOTAL': 33978, 'DP_PCT': 50.45, 'HD_INTERNA': 10926, 'HD_SUBROGADA': 22445, 'HD_TOTAL': 33371, 'HD_PCT': 49.55, 'TOTAL_PACIENTES': 67349},
        {'AÑO': 2022, 'DP_DPA': 12415, 'DP_DPCA': 21327, 'DP_TOTAL': 33742, 'DP_PCT': 48.19, 'HD_INTERNA': 12062, 'HD_SUBROGADA': 24219, 'HD_TOTAL': 36281, 'HD_PCT': 51.81, 'TOTAL_PACIENTES': 70023},
        {'AÑO': 2023, 'DP_DPA': 14663, 'DP_DPCA': 21411, 'DP_TOTAL': 36074, 'DP_PCT': 46.44, 'HD_INTERNA': 12691, 'HD_SUBROGADA': 28922, 'HD_TOTAL': 41613, 'HD_PCT': 53.56, 'TOTAL_PACIENTES': 77687},
        {'AÑO': 2024, 'DP_DPA': 16554, 'DP_DPCA': 21233, 'DP_TOTAL': 37787, 'DP_PCT': 45.14, 'HD_INTERNA': 14461, 'HD_SUBROGADA': 31456, 'HD_TOTAL': 45917, 'HD_PCT': 54.86, 'TOTAL_PACIENTES': 83704},
        {'AÑO': 2025, 'DP_DPA': 17019, 'DP_DPCA': 19579, 'DP_TOTAL': 36598, 'DP_PCT': 43.84, 'HD_INTERNA': 13427, 'HD_SUBROGADA': 33465, 'HD_TOTAL': 46892, 'HD_PCT': 56.16, 'TOTAL_PACIENTES': 83490},
        {'AÑO': 2026, 'DP_DPA': 17107, 'DP_DPCA': 19432, 'DP_TOTAL': 36539, 'DP_PCT': 43.22, 'HD_INTERNA': 13765, 'HD_SUBROGADA': 34246, 'HD_TOTAL': 48011, 'HD_PCT': 56.78, 'TOTAL_PACIENTES': 84550}
    ]
    df_hist_clin = pd.DataFrame(datos_historicos)
        
    return geo_data, df_pob, df_clin_agrupado, df_hist_clin

# --- 5. INTERFAZ Y NAVEGACIÓN ---
try:
    geo_data, df_poblacion, df_clinico, df_historico_clinico = cargar_datos_maestros()
except Exception as e:
    st.error(f"Faltan los archivos Excel en la carpeta. Error: {e}")
    st.stop()

st.sidebar.title("MAPA HISTORICO DE PACIENTES")
st.sidebar.markdown("---")
modulo_seleccionado = st.sidebar.radio(
    "Seleccione la vista de datos:",
    ("🗺️ Evolución Poblacional (Histórico)", "🏥 Auditoría Clínica (IMSS)")
)

if st.session_state.selected_state:
    if st.sidebar.button("🔄 Resetear Selección"):
        st.session_state.selected_state = None
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("Usuario: Daniela Vallejo Avalos\n\nEstado: Conectado a Base Local")

# --- 6. RENDERIZADO DEL MAPA ---

if modulo_seleccionado == "🗺️ Evolución Poblacional (Histórico)":
    st.header("Análisis Demográfico Nacional")
    st.markdown("*Use el botón de **▶ Reproducir** debajo del mapa para ver la evolución histórica animada.*")
    
    ultimo_anio = df_poblacion['AÑO'].max()
    df_ultimo = df_poblacion[df_poblacion['AÑO'] == ultimo_anio]
    col1, col2 = st.columns(2)
    col1.metric(f"Población Nacional Total ({ultimo_anio})", f"{df_ultimo['POBLACIÓN'].sum():,.0f}")
    estado_top = df_ultimo.sort_values('POBLACIÓN', ascending=False).iloc[0]
    col2.metric(f"Estado con Mayor Carga ({ultimo_anio})", estado_top['ESTADO_PADRE'], f"{estado_top['POBLACIÓN']:,.0f}")
    
    fig = px.choropleth(
        df_poblacion, geojson=geo_data, locations='ESTADO_PADRE', featureidkey="properties.name",
        color='POBLACIÓN', animation_frame='AÑO', color_continuous_scale="viridis",
        range_color=[0, df_poblacion['POBLACIÓN'].max()], custom_data=['TENDENCIA']
    )
    fig.update_traces(hovertemplate="<b>%{location}</b><br>Pacientes: %{z:,.0f}<br>Evolución: %{customdata[0]}<extra></extra>")
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=650, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

elif modulo_seleccionado == "🏥 Auditoría Clínica (IMSS)": 
    st.header("Auditoría Clínica de Tratamientos")
    
    tab1, tab2 = st.tabs(["📈 1. Reporte Histórico Nacional", "🗺️ 2. Distribución Geográfica (Corte 2016)"])
    
    with tab1:
        st.subheader("Evolución Nacional (DP vs HD)")
        anios_disponibles = sorted(df_historico_clinico['AÑO'].unique().tolist())
        anio_sel = st.select_slider("🗓️ Seleccione el Año a Consultar:", options=anios_disponibles, value=2026)
        data_anio = df_historico_clinico[df_historico_clinico['AÑO'] == anio_sel].iloc[0]
        
        st.metric("Total Nacional de Pacientes", f"{data_anio['TOTAL_PACIENTES']:,.0f}")
        col_dp, col_hd = st.columns(2)
        with col_dp:
            st.markdown(f"### 🔵 Diálisis (DP) - {data_anio['DP_PCT']}%")
            st.metric("TOTAL DP", f"{data_anio['DP_TOTAL']:,.0f}")
            c1, c2 = st.columns(2)
            c1.metric("Pacientes DPA", f"{data_anio['DP_DPA']:,.0f}")
            c2.metric("Pacientes DPCA", f"{data_anio['DP_DPCA']:,.0f}")
        with col_hd:
            st.markdown(f"### 🔴 Hemodiálisis (HD) - {data_anio['HD_PCT']}%")
            st.metric("TOTAL HD", f"{data_anio['HD_TOTAL']:,.0f}")
            c1, c2 = st.columns(2)
            c1.metric("HD Interna", f"{data_anio['HD_INTERNA']:,.0f}")
            c2.metric("HD Subrogada", f"{data_anio['HD_SUBROGADA']:,.0f}")
            
        st.markdown("---")
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(x=df_historico_clinico['AÑO'], y=df_historico_clinico['DP_TOTAL'], mode='lines+markers', name='Diálisis (DP)', line=dict(color='#3498db', width=3)))
        fig_hist.add_trace(go.Scatter(x=df_historico_clinico['AÑO'], y=df_historico_clinico['HD_TOTAL'], mode='lines+markers', name='Hemodiálisis (HD)', line=dict(color='#e74c3c', width=3)))
        fig_hist.update_layout(template="plotly_dark", height=300, margin={"r":0,"t":30,"l":0,"b":0})
        st.plotly_chart(fig_hist, use_container_width=True)

    with tab2:
        st.subheader("Auditoría Regional Activa (Corte 2016)")
        
        col_map, col_dash = st.columns([1.8, 1])
        
        with col_map:
            capa = st.radio("Ver Capa:", ["Renal Replacement Therapy 2026", "Diálisis (DP)", "Hemodiálisis (HD)"], horizontal=True)
            map_config = {"Renal Replacement Therapy 2026": ('TOTAL_PACIENTES', 'Plasma'), "Diálisis (DP)": ('TOTAL_DP', 'Blues'), "Hemodiálisis (HD)": ('TOTAL_HD', 'Reds')}
            val_col, scale = map_config[capa]

            fig_audit = go.Figure(go.Choropleth(
                geojson=geo_data, locations=df_clinico['ESTADO_PADRE'], z=df_clinico[val_col],
                featureidkey="properties.name", colorscale=scale, marker_line_color='#0d1117'
            ))
            fig_audit.update_geos(fitbounds="locations", visible=False)
            fig_audit.update_layout(
                template="plotly_dark", margin={"r":0,"t":0,"l":0,"b":0}, height=600,
                clickmode="event+select", dragmode=False
            )
            
            map_event = st.plotly_chart(fig_audit, use_container_width=True, on_select="rerun", selection_mode="points", key="audit_map")
            
            if map_event and "selection" in map_event and map_event["selection"]["points"]:
                st.session_state.selected_state = map_event["selection"]["points"][0]["location"]

        with col_dash:
            if st.session_state.selected_state:
                st.markdown(f'<div class="fade-in">', unsafe_allow_html=True)
                estado = st.session_state.selected_state
                data_est = df_clinico[df_clinico['ESTADO_PADRE'] == estado].iloc[0]
                
                st.subheader(f"📍 {estado}")
                
                fig_z = go.Figure(go.Choropleth(
                    geojson=geo_data, locations=[estado], z=[data_est[val_col]],
                    featureidkey="properties.name", colorscale=scale, showscale=False
                ))
                fig_z.update_geos(fitbounds="locations", visible=False)
                fig_z.update_layout(template="plotly_dark", height=200, margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_z, use_container_width=True, config={'displayModeBar': False})
                
                # --- MEJORA: VALORES DINÁMICOS EN LA TARJETA ---
                st.markdown(f"""
                <div class="report-card">
                    <p style="margin-bottom:5px; color:#8b949e;">{capa} Regional</p>
                    <h2 style="margin:0; color:#58a6ff;">{data_est[val_col]:,.0f}</h2>
                    <hr style="border-color:#30363d">
                    <p><b>Diálisis:</b> {data_est['TOTAL_DP']:,}</p>
                    <p><b>Hemodiálisis:</b> {data_est['TOTAL_HD']:,}</p>
                    <div style="background:#0d1117; padding:10px; border-radius:5px; margin-top:10px; font-size:0.9rem;">
                        {data_est['DESGLOSE']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Seleccione un estado en el mapa para ver el desglose detallado.")