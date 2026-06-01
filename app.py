import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime

# Configuración de pantalla optimizada para celulares
st.set_page_config(page_title="Venta de Butacas", layout="centered")

# --- 1. CONEXIÓN A LA BASE DE DATOS ---
try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL") or st.secrets.get("connections", {}).get("supabase", {}).get("url")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or st.secrets.get("connections", {}).get("supabase", {}).get("key")
    conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)
except Exception as e:
    st.error("Error en las credenciales de Supabase.")
    st.stop()

# --- 2. INICIALIZAR ESTADOS DE SESIÓN ---
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "mapa"
if "asiento_seleccionado" not in st.session_state:
    st.session_state.asiento_seleccionado = None
if "datos_butacas" not in st.session_state:
    st.session_state.datos_butacas = None

# --- 3. FUNCIÓN RÁPIDA DE CARGA (Solo viaja a internet cuando es necesario) ---
def cargar_datos_db(forzar=False):
    if st.session_state.datos_butacas is None or forzar:
        try:
            response = conn.table("butacas").select("*").execute()
            df_res = pd.DataFrame(response.data)
            if not df_res.empty:
                df_res['Fila'] = pd.to_numeric(df_res['Fila'], errors='coerce').fillna(0).astype(int)
                df_res['Asiento'] = pd.to_numeric(df_res['Asiento'], errors='coerce').fillna(0).astype(int)
                if 'Zona' in df_res.columns:
                    df_res['Zona'] = df_res['Zona'].astype(str).str.strip().str.upper()
                st.session_state.datos_butacas = df_res
        except Exception:
            st.error("Error al conectar con la base de datos.")
            st.stop()

# Cargar datos al principio si la memoria está vacía (Evita re-descargas lentas)
cargar_datos_db()

# --- 4. CONTROL DE NAVEGACIÓN INMEDIATA ---
query_params = st.query_params
if "sel_id" in query_params:
    id_id = query_params["sel_id"]
    st.query_params.clear()  # Limpiar la URL de inmediato
    
    df = st.session_state.datos_butacas
    if df is not None and not df.empty:
        asiento_local = df[df['ID_Asiento'] == id_id]
        if not asiento_local.empty:
            st.session_state.asiento_seleccionado = asiento_local.iloc[0].to_dict()
            st.session_state.pantalla = "formulario"
            st.rerun()


# =========================================================================
# PANTALLA 1: EL MAPA ULTRA COMPACTO
# =========================================================================
if st.session_state.pantalla == "mapa":
    st.markdown("<h3 style='margin-bottom: 0px;'>💺 Mapa de Asientos</h3>", unsafe_allow_html=True)
    
    # Botón discreto para actualizar manualmente por si alguien más compró
    col_tit, col_ref = st.columns([4, 1])
    with col_tit:
        st.caption("Toca un asiento de color para editar su información.")
    with col_ref:
        if st.button("🔄", help="Actualizar mapa"):
            cargar_datos_db(forzar=True)
            st.rerun()

    df = st.session_state.datos_butacas

    if df is not None and not df.empty:
        # Estilos CSS optimizados para butacas más pequeñas y adaptativas
        html_mapa = """
        <style>
            .mapa-contenedor { display: flex; flex-direction: column; gap: 2px; margin-top: 10px; }
            .fila-contenedor { display: flex; align-items: center; gap: 2px; overflow-x: auto; padding: 1px 0; }
            .label-fila { font-weight: bold; width: 28px; color: #555; font-size: 11px; text-align: center; }
            .asiento-link {
                display: inline-flex; align-items: center; justify-content: center;
                width: 19px !important; height: 19px !important; border-radius: 3px;
                font-weight: bold; font-size: 11px !important; color: white !important;
                text-decoration: none !important; border: none; text-align: center;
                padding: 0 !important; margin: 0 !important; line-height: 19px !important;
                transition: transform 0.1s;
            }
            .asiento-link:active { transform: scale(0.9); }
            .col-disponible { background-color: #2ECC71 !important; } 
            .col-ocupado { background-color: #E74C3C !important; }    
            .col-reservado { background-color: #F1C40F !important; color: #333 !important; } 
            .col-bloqueado { background-color: #7F8C8D !important; }   
        </style>
        <div class="mapa-contenedor">
        """

        zonas = ["VIP", "PLATEA", "MEZZANINE"]
        for zona in zonas:
            df_zona = df[df['Zona'] == zona]
            if df_zona.empty:
                continue
                
            html_mapa += f"<div style='font-weight:bold; margin-top:12px; margin-bottom:4px; font-size:13px; color: inherit; text-align: center;'>📌 Zona: {zona}</div>"
            filas = sorted(df_zona['Fila'].unique())
            
            for f in filas:
                html_mapa += f'<div class="fila-contenedor"><div class="label-fila">F{f}</div>'
                df_fila = df_zona[df_zona['Fila'] == f].sort_values(by='Asiento')
                
                for _, butaca in df_fila.iterrows():
                    id_asiento = butaca['ID_Asiento']
                    num_asiento = int(butaca['Asiento'])
                    estado = str(butaca['Estado']).strip()
                    
                    if estado == "Ocupado":
                        clase_color = "col-ocupado"
                    elif estado == "Reservado":
                        clase_color = "col-reservado"
                    elif estado == "Bloqueado":
                        clase_color = "col-bloqueado"
                    else:
                        clase_color = "col-disponible"
                    
                    html_mapa += f'<a href="?sel_id={id_asiento}" target="_self" class="asiento-link {clase_color}">{num_asiento}</a>'
                
                html_mapa += '</div>'
        
        html_mapa += '</div><br>'
        st.markdown(html_mapa, unsafe_allow_html=True)


# =========================================================================
# PANTALLA 2: EL FORMULARIO DE EDICIÓN (Carga instantánea)
# =========================================================================
elif st.session_state.pantalla == "formulario":
    b = st.session_state.asiento_seleccionado
    
    st.title("📝 Editar Información")
    st.subheader(f"📍 {b.get('Zona')} - Fila {b.get('Fila')}, Asiento {b.get('Asiento')}")
    
    if st.button("⬅️ Volver al Mapa", use_container_width=True):
        st.session_state.pantalla = "mapa"
        st.session_state.asiento_seleccionado = None
        st.rerun()
        
    st.write("---")
    
    with st.form("form_edicion"):
        opciones_estado = ["Disponible", "Ocupado", "Reservado", "Bloqueado"]
        estado_actual = b.get('Estado', 'Disponible')
        idx_estado = opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 0
        
        nuevo_estado = st.selectbox("Estado del asiento:", options=opciones_estado, index=idx_estado)
        
        def obtener_valor(campo):
            v = str(b.get(campo, ''))
            return "" if v.lower() in ['nan', 'none', 'null', ''] else v

        cliente = st.text_input("Nombre del Cliente:", value=obtener_valor('Datos Cliente'))
        celular = st.text_input("Celular:", value=obtener_valor('Celular'))
        vendedor = st.text_input("Vendedor:", value=obtener_valor('Vendedor'))
        cargado_por = st.text_input("Registrado Por:", value=obtener_valor('CargadoPor'))
        imagen = st.text_input("Link de Comprobante:", value=obtener_valor('Imagen'))
        
        st.write("<br>", unsafe_allow_html=True)
        guardar = st.form_submit_button("Guardar Cambios 💾", use_container_width=True)
        
    if guardar:
        with st.spinner("Guardando en Supabase..."):
            if nuevo_estado == "Disponible":
                datos_nuevos = {
                    "Estado": "Disponible", "Datos Cliente": "", "Celular": "",
                    "Vendedor": "", "CargadoPor": "", "Imagen": "", "Fecha": ""
                }
            else:
                datos_nuevos = {
                    "Estado": nuevo_estado, "Datos Cliente": cliente, "Celular": celular,
                    "Vendedor": vendedor, "CargadoPor": cargado_por, "Imagen": imagen,
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
            # Guardamos en la base de datos real
            conn.table("butacas").update(datos_nuevos).eq("ID_Asiento", b['ID_Asiento']).execute()
            
            # ⚡ OPTIMIZACIÓN CRUCIAL: Forzamos la actualización de la memoria local inmediatamente
            cargar_datos_db(forzar=True)
            
            st.session_state.pantalla = "mapa"
            st.session_state.asiento_seleccionado = None
            st.success("¡Guardado correctamente!")
            st.rerun()