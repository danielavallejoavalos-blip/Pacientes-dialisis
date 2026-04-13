import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import threading
import unicodedata
import webbrowser

# --- CONFIGURACIÓN ESTÉTICA (mantener interfaz dark para la app) ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------------------------
# UTILIDADES DE NORMALIZACIÓN
# ---------------------------
def limpiar_texto(texto):
    if pd.isna(texto): 
        return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn')

def mapeo_maestro_estados(nombre_sucio):
    n = limpiar_texto(nombre_sucio)
    mapa = {
        'mexico': 'México', 'estado de mexico': 'México', 'edomex': 'México',
        'cdmx': 'Ciudad de México', 'ciudad de mexico': 'Ciudad de México', 'distrito federal': 'Ciudad de México',
        'baja california': 'Baja California', 'baja california norte': 'Baja California',
        'baja california sur': 'Baja California Sur',
        'michoacan': 'Michoacán', 'michoacan de ocampo': 'Michoacán',
        'veracruz': 'Veracruz', 'veracruz de ignacio de la llave': 'Veracruz',
        'coahuila': 'Coahuila', 'coahuila de zaragoza': 'Coahuila',
        'queretaro': 'Querétaro', 'queretaro de arteaga': 'Querétaro',
        'san luis potosi': 'San Luis Potosí', 'yucatan': 'Yucatán', 'nuevo leon': 'Nuevo León'
    }
    base = {
        'aguascalientes', 'campeche', 'chiapas', 'chihuahua', 'colima', 'durango',
        'guanajuato', 'guerrero', 'hidalgo', 'jalisco', 'morelos', 'nayarit',
        'oaxaca', 'puebla', 'quintana roo', 'sinaloa', 'sonora', 'tabasco',
        'tamaulipas', 'tlaxcala', 'zacatecas'
    }
    if n in mapa: 
        return mapa[n]
    if n in base: 
        return n.title()
    return None

TODOS_ESTADOS = [
    'Aguascalientes','Baja California','Baja California Sur','Campeche','Chiapas',
    'Chihuahua','Ciudad de México','Coahuila','Colima','Durango','Guanajuato',
    'Guerrero','Hidalgo','Jalisco','México','Michoacán','Morelos','Nayarit',
    'Nuevo León','Oaxaca','Puebla','Querétaro','Quintana Roo','San Luis Potosí',
    'Sinaloa','Sonora','Tabasco','Tamaulipas','Tlaxcala','Veracruz','Yucatán','Zacatecas'
]

# ===================================================================
# PALETA DE COLORES SÓLIDA PROFESIONAL (para revista Q1-Q2)
# ===================================================================
# Colores sólidos y saturados siguiendo convenciones cartográficas:
# Bajo → Vegetación/tierras bajas (verde) → Transición tierra → Alto (marrón-rojizo)
# Agua reservada para azul cian sólido (no se usa para territorio)
custom_colorscale = [
    [0.0,  '#A1D4FF'],   # Agua / valores muy bajos (cian sólido)
    [0.15, '#7CC46A'],   # Tierras bajas y vegetación (verde saturado)
    [0.35, '#C9B37F'],   # Transición
    [0.55, '#D9A46F'],   # Elevaciones / población media (marrón claro sólido)
    [0.75, '#C17F4E'],   # Población alta (marrón medio)
    [0.90, '#9B5A2F'],   # Muy alta (marrón oscuro)
    [1.0,  '#8B3D1E']    # Máxima población (rojizo-marrón sólido)
]

# ===================================================================
# APLICACIÓN PRINCIPAL
# ===================================================================
class VisionMapElite(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mapa Evolución Pacientes | Daniela Vallejo Avalos")
        self.geometry("1100x750")
       
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=280, fg_color="#0d1117", corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.lbl_logo = ctk.CTkLabel(self.sidebar, text="MAPA INTERACTIVO IMSS", 
                                     font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_logo.pack(pady=(40, 5))
       
        self.lbl_status = ctk.CTkLabel(self.sidebar, text="SISTEMA LISTO", 
                                       text_color="#2ecc71", font=("Arial", 11, "bold"))
        self.lbl_status.pack(pady=(0, 20))
        
        self.btn_import = ctk.CTkButton(self.sidebar, text="📂 PROCESAR EXCEL",
                                        command=self.iniciar_hilo, height=40, 
                                        font=("Arial", 13, "bold"))
        self.btn_import.pack(pady=10, padx=20, fill="x")
        
        self.txt_console = ctk.CTkTextbox(self.sidebar, fg_color="#010409", 
                                          font=("Consolas", 11), text_color="#7f8c8d")
        self.txt_console.pack(fill="both", expand=True, padx=15, pady=20)

        # --- MAIN PANEL ---
        self.main = ctk.CTkFrame(self, fg_color="#010409")
        self.main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.lbl_header = ctk.CTkLabel(self.main, text="Evolución de Población", 
                                       font=ctk.CTkFont(size=28, weight="bold"))
        self.lbl_header.pack(pady=(20, 5), anchor="w")
        
        self.prog_bar = ctk.CTkProgressBar(self.main, height=12, progress_color="#3498db")
        self.prog_bar.pack(fill="x", pady=20)
        self.prog_bar.set(0)

    def log(self, txt):
        self.txt_console.insert("end", f"> {txt}\n")
        self.txt_console.see("end")

    def iniciar_hilo(self):
        self.btn_import.configure(state="disabled")
        self.lbl_status.configure(text="PROCESANDO...", text_color="#f1c40f")
        threading.Thread(target=self.pipeline, daemon=True).start()

    def pipeline(self):
        ruta = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            self.btn_import.configure(state="normal")
            self.lbl_status.configure(text="SISTEMA LISTO", text_color="#2ecc71")
            return

        try:
            self.log("Leyendo Base de Datos...")
            self.prog_bar.set(0.2)
            
            df = pd.read_excel(ruta, sheet_name='POBLACION POR ESTADO')

            # 1. LIMPIEZA Y FORMATEO
            df['AÑO'] = df['AÑO'].ffill().astype(int)
            df['POBLACIÓN'] = df['POBLACIÓN'].astype(str).str.replace(' ', '', regex=False)
            df['POBLACIÓN'] = pd.to_numeric(df['POBLACIÓN'], errors='coerce').fillna(0)

            # 2. MAPEO DE ESTADOS
            df['ESTADO'] = df['ESTADO'].apply(mapeo_maestro_estados)
            df = df.dropna(subset=['ESTADO'])

            # 3. NORMALIZACIÓN (completar estados faltantes)
            df_completo = []
            for anio in sorted(df['AÑO'].unique()):
                df_anio = df[df['AÑO'] == anio].copy()
                faltantes = set(TODOS_ESTADOS) - set(df_anio['ESTADO'])
                if faltantes:
                    df_faltante = pd.DataFrame([{'AÑO': anio, 'ESTADO': e, 'POBLACIÓN': 0} 
                                              for e in faltantes])
                    df_anio = pd.concat([df_anio, df_faltante])
                
                df_anio['RANK'] = df_anio['POBLACIÓN'].rank(ascending=False, method='min').astype(int)
                df_anio['%_NACIONAL'] = (df_anio['POBLACIÓN'] / df_anio['POBLACIÓN'].sum() * 100).round(2)
                df_completo.append(df_anio)

            df = pd.concat(df_completo, ignore_index=True)
            self.prog_bar.set(0.5)
            self.log("Sincronizando Cartografía (GeoJSON)...")

            geo_data = requests.get("https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json").json()

            # 4. CONSTRUCCIÓN DEL DASHBOARD CON COLORES PROFESIONALES
            anios = sorted(df['AÑO'].unique())
            fig = make_subplots(
                rows=1, cols=2, column_widths=[0.65, 0.35],
                specs=[[{"type": "choropleth"}, {"type": "bar"}]],
                subplot_titles=('Distribución Geográfica de Población', 'Ranking de Estados (Top 15)')
            )

            frames = []
            for anio in anios:
                df_anio_map = df[df['AÑO'] == anio].sort_values('ESTADO')
                df_top_bar = df[df['AÑO'] == anio].sort_values('POBLACIÓN', ascending=False).head(15)

                frames.append(go.Frame(
                    data=[
                        go.Choropleth(
                            geojson=geo_data,
                            locations=df_anio_map['ESTADO'],
                            z=df_anio_map['POBLACIÓN'],
                            featureidkey="properties.name",
                            colorscale=custom_colorscale,      # ← Nueva paleta sólida
                            zmin=0,
                            zmax=df['POBLACIÓN'].max(),
                            hovertemplate="<b>%{location}</b><br>Población: %{z:,.0f}<br>Rank: %{customdata[0]}°<br>% Nacional: %{customdata[1]}%<extra></extra>",
                            customdata=df_anio_map[['RANK', '%_NACIONAL']],
                            colorbar=dict(title="Población", thickness=15)
                        ),
                        go.Bar(
                            x=df_top_bar['POBLACIÓN'], 
                            y=df_top_bar['ESTADO'],
                            orientation='h',
                            marker=dict(color=df_top_bar['POBLACIÓN'], colorscale=custom_colorscale),
                            text=[f" {v:,.0f}" for v in df_top_bar['POBLACIÓN']],
                            textposition='outside'
                        )
                    ],
                    name=str(anio)
                ))

            # Agregar primer frame
            fig.add_trace(frames[0].data[0], row=1, col=1)
            fig.add_trace(frames[0].data[1], row=1, col=2)

            # DISEÑO PROFESIONAL CON FONDO BLANCO
            fig.update_layout(
                template="plotly_white",                    # Base blanca
                paper_bgcolor="#FFFFFF",                    # Fondo exterior blanco
                plot_bgcolor="#FFFFFF",                     # Fondo del gráfico blanco
                margin={"r":30, "t":80, "l":30, "b":50},
                title=dict(
                    text="Evolución de la Población por Entidad Federativa en México",
                    x=0.5,
                    font=dict(size=20)
                ),
                updatemenus=[{
                    "buttons": [
                        {"args": [None, {"frame": {"duration": 800, "redraw": True}, "fromcurrent": True}], 
                         "label": "▶ Play", "method": "animate"},
                        {"args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}], 
                         "label": "⏸ Pause", "method": "animate"}
                    ],
                    "type": "buttons", "showactive": False, "x": 0.05, "y": -0.12
                }],
                sliders=[{
                    "steps": [{"args": [[str(a)], {"frame": {"duration": 300, "redraw": True}, "mode": "immediate"}], 
                              "label": str(a), "method": "animate"} for a in anios],
                    "x": 0.15, "len": 0.80, "currentvalue": {"prefix": "Año: "}
                }]
            )

            fig.frames = frames

            # Configuración geográfica + fondo blanco para agua y mapa
            fig.update_geos(
                fitbounds="locations",
                visible=False,
                projection_type="mercator",
                bgcolor="#FFFFFF",           # Fondo del mapa blanco
                showlakes=True,
                lakecolor="#A1D4FF",         # Agua en cian sólido (coherente con colorscale)
                oceancolor="#A1D4FF"
            )

            # Guardar y abrir
            salida = os.path.join(os.path.dirname(ruta), "Mapa_Interactivo_Publicacion.html")
            fig.write_html(salida, config={'scrollZoom': True, 'displayModeBar': True})
            
            webbrowser.open(salida)
            self.prog_bar.set(1.0)
            self.lbl_status.configure(text="COMPLETADO", text_color="#2ecc71")
            self.log(f"Dashboard generado: {os.path.basename(salida)}")
            messagebox.showinfo("Éxito", f"Archivo generado correctamente en:\n{salida}\n\nListo para revista (fondo blanco + colores sólidos).")

        except Exception as e:
            self.log(f"ERROR CRÍTICO: {e}")
            self.lbl_status.configure(text="ERROR EN SISTEMA", text_color="#e74c3c")
       
        finally:
            self.btn_import.configure(state="normal")


if __name__ == "__main__":
    app = VisionMapElite()
    app.mainloop()
    
