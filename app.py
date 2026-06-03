import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime, timedelta

def generar_imagen_comprobante(b):
    try:
        img = Image.open("Boleto9.png").convert('RGB') 
    except FileNotFoundError:
        img = Image.new('RGB', (400, 500), color=(255, 255, 255))
    
    d = ImageDraw.Draw(img)
    
    try:
        fuente_titulo = ImageFont.truetype("Ticketing.ttf", 20)
        fuente_texto = ImageFont.truetype("Ticketing.ttf", 35)
    except IOError:
        fuente_titulo = ImageFont.load_default()
        fuente_texto = ImageFont.load_default()
    
    # --- PROCESAR LA FECHA GUARDADA ---
    fecha_guardada = b.get('Fecha', '')
    fecha_mostrar = ""

    if fecha_guardada and str(fecha_guardada).lower() not in ['nan', 'none', 'null', '']:
        try:
            # Supabase suele guardar la fecha como 'YYYY-MM-DD HH:MM:SS'
            # Lo convertimos a un objeto datetime para darle un formato más bonito
            dt = datetime.strptime(str(fecha_guardada).split(".")[0], "%Y-%m-%d %H:%M:%S")
            fecha_mostrar = dt.strftime('%d/%m/%Y %H:%M')
        except ValueError:
            # Si por alguna razón el formato de la cadena varía, mostramos el texto tal cual viene
            fecha_mostrar = str(fecha_guardada)
    else:
        fecha_mostrar = "No registrada"

    # --- DIBUJAR LOS TEXTOS ---
    d.text((130, 625), f"ASIENTO: {b.get('Asiento')}", fill=(255, 255, 255), font=fuente_texto)
    d.text((130, 670), f"FILA: {b.get('Fila')}", fill=(255, 255, 255), font=fuente_texto)
    d.text((130, 715), f"ZONA: {b.get('Zona')}", fill=(255, 255, 255), font=fuente_texto)
    d.text((130, 750), f"CLIENTE: {b.get('Datos Cliente')}", fill=(255, 255, 255), font=fuente_texto)
    d.text((130, 795), f"VENDEDOR: {b.get('Vendedor')}", fill=(255, 255, 255), font=fuente_texto)
    d.text((130, 840), f"FECHA VENTA: {fecha_mostrar}", fill=(255, 255, 255), font=fuente_texto)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

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

@st.dialog("📝 Editar Información")
def mostrar_formulario_modal(b):
    st.markdown(f"📍 **{b.get('Zona')}** — Fila {b.get('Fila')}, Asiento {b.get('Asiento')}")
    
    # Mensaje de éxito persistente tras guardar
    if st.session_state.get("guardado_reciente_id") == b['ID_Asiento']:
        st.success("¡Guardado correctamente!")
        st.session_state["guardado_reciente_id"] = None

    # Opciones de Estado usando st.pills
    opciones_estado = ["Disponible", "Ocupado", "Reservado", "Bloqueado"]
    estado_actual = b.get('Estado', 'Disponible')
    idx_estado = opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 0
    
    # Agregamos una clave única (key) para evitar conflictos en re-ejecuciones
    nuevo_estado = st.pills("Estado del asiento:", options=opciones_estado, default=opciones_estado[idx_estado], key=f"pill_{b['ID_Asiento']}")
    
    def obtener_valor(campo):
        v = str(b.get(campo, ''))
        return "" if v.lower() in ['nan', 'none', 'null', ''] else v

    # Inputs de texto normales con claves únicas asociadas al ID del asiento
    cliente = st.text_input("Nombre del Cliente:", value=obtener_valor('Datos Cliente'), key=f"cli_{b['ID_Asiento']}")
    celular = st.text_input("Celular:", value=obtener_valor('Celular'), key=f"cel_{b['ID_Asiento']}")
    vendedor = st.text_input("Vendedor:", value=obtener_valor('Vendedor'), key=f"ven_{b['ID_Asiento']}")
    
    st.write("<br>", unsafe_allow_html=True)
    
    # Botón normal de Streamlit
    guardar = st.button("Guardar", use_container_width=True)
        
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
                    "Vendedor": vendedor, "Fecha": (datetime.utcnow() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
                }
                
            # Guardar en Supabase
            conn.table("butacas").update(datos_nuevos).eq("ID_Asiento", b['ID_Asiento']).execute()
            
            # Guardar Historial
            datos_historial = {
                "id_asiento": str(b.get('ID_Asiento')),
                "zona": str(b.get('Zona')),
                "fila": int(b.get('Fila', 0)),
                "asiento": int(b.get('Asiento', 0)),
                "estado_anterior": str(b.get('Estado', 'Disponible')),
                "estado_nuevo": nuevo_estado,
                "cliente": cliente,
                "celular": celular,
                "vendedor": vendedor
            }
            try:
                conn.table("historial_butacas").insert(datos_historial).execute()
            except Exception:
                pass

            # Refrescamos la BD local inmediatamente
            cargar_datos_db(forzar=True)
            
            # Guardamos la bandera para el mensaje de éxito
            st.session_state["guardado_reciente_id"] = b['ID_Asiento']
            
            # Limpiamos los query params para asegurarnos de que el mapa de fondo no intente duplicar llamadas
            st.query_params.clear()
            # Forzamos la reapertura limpia del formulario pasándole los nuevos datos directamente
            st.query_params["sel_id"] = b['ID_Asiento']
            st.rerun()

    # --- BOTÓN DE DESCARGA DINÁMICO ---
    if estado_actual in ["Ocupado", "Reservado"]:
        img_bytes = generar_imagen_comprobante(b)
        st.download_button(
            label="Descargar Boleto",
            data=img_bytes,
            file_name=f"Boleto_{b.get('Zona')}_{b.get('Fila')}_{b.get('Asiento')}.png",
            mime="image/png",
            use_container_width=True,
            key=f"dl_{b['ID_Asiento']}" # Clave única para evitar errores de duplicados
        )

# --- 4. DETECTAR CLIC INMEDIATO DESDE EL MAPA O REFRESCADO DE FORMULARIO ---
query_params = st.query_params
if "sel_id" in query_params:
    id_id = query_params["sel_id"]
    st.query_params.clear()  # Limpia la URL inmediatamente
    
    df = st.session_state.datos_butacas
    if df is not None and not df.empty:
        asiento_local = df[df['ID_Asiento'] == id_id]
        if not asiento_local.empty:
            mostrar_formulario_modal(asiento_local.iloc[0].to_dict())


## =========================================================================
# PANTALLA PRINCIPAL: MAPA
## =========================================================================

st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
        <h3 style="margin: 0; padding: 0;">JARDÍN DE MELODIAS</h3>
        <a href="?refresh=true" target="_self" style="
            text-decoration: none; 
            background-color: var(--secondary-background-color, #f0f2f6); 
            color: var(--text-color, #31333F); 
            padding: 4px 10px; 
            border-radius: 4px; 
            font-size: 14px; 
            font-weight: bold;
            border: 1px solid rgba(49, 51, 63, 0.2);
        ">🔄</a>
    </div>
""", unsafe_allow_html=True)

if st.query_params.get("refresh") == "true":
    st.query_params.clear()
    cargar_datos_db(forzar=True)
    st.rerun()

df = st.session_state.datos_butacas

if df is not None and not df.empty:
    html_mapa = """
    <style>
        .mapa-contenedor { display: flex; flex-direction: column; gap: 4px; margin-top: 10px; }
        .fila-contenedor { 
            display: flex; 
            align-items: center; 
            justify-content: flex-start; 
            gap: 1px; 
            padding: 1px 0; 
            width: 100%;
            overflow: hidden; 
            white-space: nowrap;
            margin-left: 2px; 
        }
        .label-fila { 
            font-weight: bold; 
            width: 34px !important; 
            min-width: 34px !important; 
            max-width: 34px !important; 
            color: var(--text-color) !important; 
            opacity: 0.6;
            font-size: 10px; 
            text-align: center; 
            margin-right: 4px; 
            display: inline-block; 
        }
        .asiento-link {
            display: inline-block; 
            width: 19px !important; 
            height: 14px !important; 
            line-height: 14px !important; 
            border-radius: 3px;
            font-weight: bold; font-size: 11px !important; color: white !important;
            text-decoration: none !important; border: none; text-align: center;
            padding: 0 !important; margin: 0 !important; 
            transition: transform 0.1s;
        }
        .asiento-link:active { transform: scale(0.9); }
        .asiento-vacio {
            display: inline-block;
            width: 19px !important; 
            height: 14px !important; 
            padding: 0 !important; margin: 0 !important;
        }
        .seccion-titulo {
            font-weight: bold;
            margin-top: 10px;    
            margin-bottom: 4px;   
            font-size: 12px;      
            text-align: center;
            color: var(--text-color) !important; 
            opacity: 0.85; 
        }
        .escenario {
            background-color: #34495E;
            color: white;
            text-align: center;
            padding: 6px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
            margin-bottom: 6px; 
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
            html_mapa += '<div class="seccion-titulo">PLATEA</div>'

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
