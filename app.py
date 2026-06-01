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
if "datos_butacas" not in st.session_state:
    st.session_state.datos_butacas = None

# --- 3. FUNCIÓN RÁPIDA DE CARGA ---
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

# Cargar datos iniciales
cargar_datos_db()


# =========================================================================
# NUEVO: MODAL FLOTANTE DE EDICIÓN (Reemplaza la Pantalla 2 anterior)
# =========================================================================
@st.dialog("📝 Editar Información")
def mostrar_formulario_modal(b):
    st.markdown(f"📍 **{b.get('Zona')}** — Fila {b.get('Fila')}, Asiento {b.get('Asiento')}")
    
    with st.form("form_edicion_rapida"):
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
        
        # 'Registrado Por' eliminado de aquí
                
        st.write("<br>", unsafe_allow_html=True)
        guardar = st.form_submit_button("Guardar Cambios 💾", use_container_width=True)
        
    if guardar:
        with st.spinner("Guardando..."):
            if nuevo_estado == "Disponible":
                datos_nuevos = {
                    "Estado": "Disponible", "Datos Cliente": "", "Celular": "",
                    "Vendedor": "", "Fecha": ""
                }
            else:
                datos_nuevos = {
                    "Estado": nuevo_estado, "Datos Cliente": cliente, "Celular": celular,
                    "Vendedor": vendedor, "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
            conn.table("butacas").update(datos_nuevos).eq("ID_Asiento", b['ID_Asiento']).execute()
            cargar_datos_db(forzar=True)
            st.success("¡Guardado correctamente!")
            st.rerun()  # Cierra el modal y refresca el mapa al instante


# --- 4. DETECTAR CLIC INMEDIATO DESDE EL MAPA ---
query_params = st.query_params
if "sel_id" in query_params:
    id_id = query_params["sel_id"]
    st.query_params.clear()  # Limpia la URL inmediatamente
    
    df = st.session_state.datos_butacas
    if df is not None and not df.empty:
        asiento_local = df[df['ID_Asiento'] == id_id]
        if not asiento_local.empty:
            mostrar_formulario_modal(asiento_local.iloc[0].to_dict())


# =========================================================================
# PANTALLA PRINCIPAL: MAPA
# =========================================================================
st.markdown("<h3 style='margin-bottom: 0px;'>💺 Mapa de Asientos</h3>", unsafe_allow_html=True)

col_tit, col_ref = st.columns([4, 1])
with col_tit:
    st.caption("Toca un asiento de color para editar su información.")
with col_ref:
    if st.button("🔄", help="Actualizar mapa"):
        cargar_datos_db(forzar=True)
        st.rerun()

df = st.session_state.datos_butacas

if df is not None and not df.empty:
    html_mapa = """
    <style>
        .mapa-contenedor { display: flex; flex-direction: column; gap: 4px; margin-top: 10px; }
        .fila-contenedor { display: flex; align-items: center; justify-content: center; gap: 2px; padding: 1px 0; }
        .label-fila { font-weight: bold; width: 28px; color: #555; font-size: 11px; text-align: center; margin-right: 4px; }
        .asiento-link {
            display: inline-flex; align-items: center; justify-content: center;
            width: 19px !important; height: 19px !important; border-radius: 3px;
            font-weight: bold; font-size: 11px !important; color: white !important;
            text-decoration: none !important; border: none; text-align: center;
            padding: 0 !important; margin: 0 !important; line-height: 19px !important;
            transition: transform 0.1s;
        }
        .asiento-link:active { transform: scale(0.9); }
        .asiento-vacio {
            display: inline-block;
            width: 19px !important; height: 19px !important;
            padding: 0 !important; margin: 0 !important;
        }
        .seccion-titulo {
            font-weight: bold;
            margin-top: 22px;
            margin-bottom: 8px;
            font-size: 13px;
            text-align: center;
            color: #2C3E50;
        }
        .escenario {
            background-color: #34495E;
            color: white;
            text-align: center;
            padding: 6px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
            margin-bottom: 15px;
            letter-spacing: 2px;
        }
        .col-disponible { background-color: #2ECC71 !important; } 
        .col-ocupado { background-color: #E74C3C !important; }    
        .col-reservado { background-color: #F1C40F !important; color: #333 !important; } 
        .col-bloqueado { background-color: #7F8C8D !important; }   
    </style>
    <div class="mapa-contenedor">
        <div class="escenario">ESCENARIO</div>
    """

    # --- 1. TITULO: VIP ---
    html_mapa += '<div class="seccion-titulo">VIP</div>'
    
    estructura_inferior = {
        1: {"v_izq": 4, "asientos": (19, 1), "v_der": 2},
        2: {"v_izq": 3, "asientos": (21, 1), "v_der": 1},
        3: {"v_izq": 2, "asientos": (22, 1), "v_der": 1},
        **{r: {"v_izq": 1, "asientos": (23, 1), "v_der": 1} for r in range(4, 15)}
    }

    for f in range(1, 15):
        df_fila = df[(df['Fila'] == f) & (df['Zona'].isin(['VIP', 'PLATEA']))]
        config = estructura_inferior.get(f, {"v_izq": 0, "asientos": (0, 0), "v_der": 0})
        
        html_mapa += f'<div class="fila-contenedor"><div class="label-fila">F{f}</div>'
        
        for _ in range(config["v_izq"]):
            html_mapa += '<div class="asiento-vacio"></div>'
            
        inicio, fin = config["asientos"]
        if inicio > 0:
            for num in range(inicio, fin - 1, -1):
                butaca = df_fila[df_fila['Asiento'] == num]
                if not butaca.empty:
                    b_data = butaca.iloc[0]
                    estado = str(b_data['Estado']).strip()
                    id_asiento = b_data['ID_Asiento']
                    clase_color = "col-ocupado" if estado == "Ocupado" else "col-reservado" if estado == "Reservado" else "col-bloqueado" if estado == "Bloqueado" else "col-disponible"
                    html_mapa += f'<a href="?sel_id={id_asiento}" target="_self" class="asiento-link {clase_color}">{num}</a>'
                else:
                    html_mapa += '<div class="asiento-vacio"></div>'
        
        for _ in range(config["v_der"]):
            html_mapa += '<div class="asiento-vacio"></div>'
            
        html_mapa += '</div>'
        
        if f == 7:
            html_mapa += '<div class="seccion-titulo">ZONA PLATEA</div>'

    # --- 2. TITULO: MEZZANINE ---
    df_mezz = df[df['Zona'] == 'MEZZANINE']
    if not df_mezz.empty:
        html_mapa += '<div class="seccion-titulo">MEZZANINE</div>'
        
        estructura_mezz = {
            4: [("v", 0), ("a", (12, 7)), ("v", 13), ("a", (6, 1)), ("v", 0)],
            3: [("v", 0), ("a", (23, 18)), ("v", 1), ("a", (17, 7)), ("v", 1), ("a", (6, 1)), ("v", 0)],
            2: [("v", 1), ("a", (20, 16)), ("v", 2), ("a", (15, 6)), ("v", 1), ("a", (5, 1)), ("v", 1)],
            1: [("v", 1), ("a", (21, 17)), ("v", 1), ("a", (16, 6)), ("v", 1), ("a", (5, 1)), ("v", 1)]
        }
        
        for f in [1, 2, 3, 4]:
            html_mapa += f'<div class="fila-contenedor"><div class="label-fila">M-F{f}</div>'
            df_fila = df_mezz[df_mezz['Fila'] == f]
            
            bloques = estructura_mezz.get(f, [])
            for tipo, info in bloques:
                if tipo == "v":
                    for _ in range(info):
                        html_mapa += '<div class="asiento-vacio"></div>'
                elif tipo == "a":
                    inicio, fin = info
                    for num in range(inicio, fin - 1, -1):
                        butaca = df_fila[df_fila['Asiento'] == num]
                        if not butaca.empty:
                            b_data = butaca.iloc[0]
                            estado = str(b_data['Estado']).strip()
                            id_asiento = b_data['ID_Asiento']
                            clase_color = "col-ocupado" if estado == "Ocupado" else "col-reservado" if estado == "Reservado" else "col-bloqueado" if estado == "Bloqueado" else "col-disponible"
                            html_mapa += f'<a href="?sel_id={id_asiento}" target="_self" class="asiento-link {clase_color}">{num}</a>'
                        else:
                            html_mapa += '<div class="asiento-vacio"></div>'
            html_mapa += '</div>'

    html_mapa += '</div><br>'
    st.markdown(html_mapa, unsafe_allow_html=True)
