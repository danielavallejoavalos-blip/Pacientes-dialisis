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
        if key in
