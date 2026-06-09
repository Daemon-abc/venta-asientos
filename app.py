import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
import io

# --- FORZAR PERMISO DE ZOOM EN CELULARES ---
# --- FORZAR PERMISO DE ZOOM EN CELULARES (COMPATIBLE CON STREAMLIT CLOUD) ---
# --- FORZAR PERMISO DE ZOOM EN CELULARES (COMPATIBLE CON STREAMLIT CLOUD) ---
st.markdown(
    """
    <script>
        // Función para romper el bloqueo de zoom de Streamlit en el navegador del celular
        const habilitarZoomMovi = () => {
            // Modifica el viewport de la app activa
            const viewportsActuales = document.querySelectorAll('meta[name="viewport"]');
            viewportsActuales.forEach(vp => {
                vp.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes');
            });
            
            // Modifica el viewport del contenedor padre de Streamlit Cloud
            if (window.parent && window.parent.document) {
                const viewportsPadre = window.parent.document.querySelectorAll('meta[name="viewport"]');
                viewportsPadre.forEach(vp => {
                    vp.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes');
                });
            }
        };

        // Se ejecuta al cargar y se repite continuamente por si Streamlit refresca la página
        habilitarZoomMovi();
        setInterval(habilitarZoomMovi, 1500);
    </script>
    """, 
    unsafe_allow_html=True
)

def generar_imagen_comprobante(b):
    try:
        img = Image.open("ticked-02.png").convert('RGB') 
    except FileNotFoundError:
        img = Image.new('RGB', (640, 800), color=(255, 255, 255))
    
    d = ImageDraw.Draw(img)
    
    try:
        fuente_titulo = ImageFont.truetype("Ticketing.ttf", 60)
        fuente_texto = ImageFont.truetype("Ticketing.ttf", 20)
    except IOError:
        fuente_titulo = ImageFont.load_default()
        fuente_texto = ImageFont.load_default()
    
    # --- PROCESAR LA FECHA GUARDADA ---
    fecha_guardada = b.get('Fecha', '')
    fecha_mostrar = ""

    if fecha_guardada and str(fecha_guardada).lower() not in ['nan', 'none', 'null', '']:
        try:
            dt = datetime.strptime(str(fecha_guardada).split(".")[0], "%Y-%m-%d %H:%M:%S")
            fecha_mostrar = dt.strftime('%d/%m/%Y %H:%M')
        except ValueError:
            fecha_mostrar = str(fecha_guardada)
    else:
        fecha_mostrar = "No registrada"

    # --- DIBUJAR LOS TEXTOS CENTRADOS ---
    d.text((320, 470), f"ASIENTO: {b.get('Asiento')}", fill=(255, 255, 255), font=fuente_titulo, anchor="mm")
    d.text((320, 530), f"FILA: {b.get('Fila')}", fill=(255, 255, 255), font=fuente_titulo, anchor="mm")
    d.text((320, 590), f"ZONA: {b.get('Zona')}", fill=(255, 255, 255), font=fuente_titulo, anchor="mm")
    d.text((320, 635), f"CLIENTE: {b.get('Datos Cliente')}", fill=(255, 255, 255), font=fuente_texto, anchor="mm")
    d.text((320, 660), f"CELULAR: {b.get('Celular')}", fill=(255, 255, 255), font=fuente_texto, anchor="mm")
    d.text((320, 685), f"VENDEDOR: {b.get('Vendedor')}", fill=(255, 255, 255), font=fuente_texto, anchor="mm")
    d.text((320, 710), f"FECHA VENTA: {fecha_mostrar}", fill=(255, 255, 255), font=fuente_texto, anchor="mm")
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

@st.dialog("EDITAR INFORMACIÓN")
def mostrar_formulario_modal(b):
    st.markdown(f"**{b.get('Zona')}** — **Fila {b.get('Fila')}** — **Asiento {b.get('Asiento')}**")
    
    if st.session_state.get("guardado_reciente_id") == b['ID_Asiento']:
        st.success("¡Guardado correctamente!")
        st.session_state["guardado_reciente_id"] = None

    opciones_estado = ["Disponible", "Ocupado", "Reservado", "Bloqueado"]
    estado_actual = b.get('Estado', 'Disponible')
    idx_estado = opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 0
    
    nuevo_estado = st.pills("Estado del asiento:", options=opciones_estado, default=opciones_estado[idx_estado], key=f"pill_{b['ID_Asiento']}")
    
    def obtener_valor(campo):
        v = str(b.get(campo, ''))
        return "" if v.lower() in ['nan', 'none', 'null', ''] else v

    cliente = st.text_input("Nombre del Cliente:", value=obtener_valor('Datos Cliente'), key=f"cli_{b['ID_Asiento']}")
    celular = st.text_input("Celular:", value=obtener_valor('Celular'), key=f"cel_{b['ID_Asiento']}")
    vendedor = st.text_input("Vendedor:", value=obtener_valor('Vendedor'), key=f"ven_{b['ID_Asiento']}")
    
    st.write("<br>", unsafe_allow_html=True)
    guardar = st.button("Guardar", use_container_width=True)
        
    if guardar:
        with st.spinner("Guardando..."):
            if nuevo_estado == "Disponible":
                datos_nuevos = {
                    "Estado": "Disponible", "Datos Cliente": "", "Celular": "",
                    "Vendedor": "", "Fecha": ""
                }
            else:
                # Zona horaria fija UTC-4 de forma limpia y moderna
                hora_local = datetime.now(timezone(timedelta(hours=-4)))
                datos_nuevos = {
                    "Estado": nuevo_estado, "Datos Cliente": cliente, "Celular": celular,
                    "Vendedor": vendedor, "Fecha": hora_local.strftime("%Y-%m-%d %H:%M:%S")
                }
                
            conn.table("butacas").update(datos_nuevos).eq("ID_Asiento", b['ID_Asiento']).execute()
            
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

            cargar_datos_db(forzar=True)
            st.session_state["guardado_reciente_id"] = b['ID_Asiento']
            st.query_params.clear()
            st.query_params["sel_id"] = b['ID_Asiento']
            st.rerun()

    if estado_actual in ["Ocupado", "Reservado"]:
        img_bytes = generar_imagen_comprobante(b)
        st.download_button(
            label="Descargar",
            data=img_bytes,
            file_name=f"Boleto_{b.get('Zona')}_{b.get('Fila')}_{b.get('Asiento')}.png",
            mime="image/png",
            use_container_width=True,
            key=f"dl_{b['ID_Asiento']}"
        )

# --- 4. DETECTAR CLIC INMEDIATO DESDE EL MAPA ---
query_params = st.query_params
if "sel_id" in query_params:
    id_id = query_params["sel_id"]
    st.query_params.clear()
    
    df = st.session_state.datos_butacas
    if df is not None and not df.empty:
        asiento_local = df[df['ID_Asiento'] == id_id]
        if not asiento_local.empty:
            mostrar_formulario_modal(asiento_local.iloc[0].to_dict())

## =========================================================================
# PANTALLA PRINCIPAL: MAPA
## =========================================================================
df = st.session_state.datos_butacas

if df is not None and not df.empty:
    css_estilos = """<style>
    /* Ocultamos por completo la cadenita de Streamlit de los h3 */
    .titulo-principal h3 a, 
    .titulo-principal a, 
    h3 a.header-anchor {
        opacity: 0 !important;
        position: absolute !important;
        left: -9999px !important;
        width: 0 !important;
        height: 0 !important;
    }

    .titulo-principal {
        width: 100% !important;
        text-align: center !important;
        margin-top: 10px !important;
        margin-bottom: 15px !important;
        display: block !important;
    }

    /* Corrección del bloque h3 para que se centre perfectamente */
    .titulo-principal h3 {
        margin: 0 auto !important;
        padding: 0 !important;
        text-align: center !important;
        font-weight: bold !important;
        display: block !important; 
    }

    .contenedor-maestro-mapa {
        width: 100%; 
        max-width: 100%; 
        display: block; 
        box-sizing: border-box;
        position: relative !important;
    }

    .pantalla-layout { 
        display: flex !important; 
        flex-direction: row !important; 
        align-items: stretch !important; 
        justify-content: center !important;
        width: 100% !important; 
        max-width: 100% !important;
        margin-top: 10px; 
        box-sizing: border-box !important;
        position: relative !important;
        overflow: hidden !important;
    }
    
    .mapa-seccion { 
        flex-grow: 1 !important;
        flex-shrink: 1 !important;
        display: block !important; 
        max-width: calc(100% - 50px) !important;
        overflow-x: auto !important;
    }
    
    .mapa-contenedor { 
        display: flex !important; 
        flex-direction: column !important; 
        gap: 2px !important; 
        align-items: center !important;
    }
    
    .fila-contenedor { 
        display: flex !important; 
        flex-direction: row !important; 
        align-items: center !important; 
        justify-content: center !important;
        gap: 0.15vw !important; 
        padding: 0px 0 !important; 
        width: 100% !important; 
        max-width: 460px !important;
        white-space: nowrap !important; 
    }
    
    .label-fila { 
        font-weight: bold !important; 
        width: 7vw !important; 
        min-width: 20px !important;
        max-width: 40px !important;
        color: var(--text-color) !important; 
        opacity: 0.6 !important; 
        font-size: 1.8vw !important; 
        text-align: center !important; 
        margin-right: 0.2vw !important; 
        display: inline-block !important; 
    }
    
    .label-fila-derecha { 
        font-weight: bold !important; 
        width: 7vw !important; 
        min-width: 20px !important;
        max-width: 40px !important;
        color: var(--text-color) !important; 
        opacity: 0.6 !important; 
        font-size: 1.8vw !important; 
        text-align: center !important; 
        margin-left: 0.2vw !important; 
        display: inline-block !important; 
    }
    
    .zonas-lateral { 
        display: flex !important; 
        flex-direction: column !important; 
        justify-content: space-between !important; 
        align-items: center !important; 
        width: 20px !important;
        min-width: 15px !important; 
        max-width: 25px !important;
        height: auto !important;
        align-self: stretch !important; 
        flex-shrink: 0 !important;
    }

    .asiento-link { 
        display: inline-block !important; 
        width: 3.2vw !important; 
        max-width: 16px !important;
        height: 3vw !important; 
        max-height: 16px !important;
        line-height: 3.2vw !important; 
        border-radius: 2px !important; 
        font-weight: bold !important; 
        font-size: 1.5vw !important; 
        color: white !important; 
        text-decoration: none !important; 
        border: none !important; 
        text-align: center !important; 
        padding: 0 !important; 
        margin: 0 !important; 
        transition: transform 0.1s !important; 
    }
    .asiento-link:active { transform: scale(0.9) !important; }
    
    .asiento-vacio { 
        display: inline-block !important; 
        width: 3.2vw !important; 
        max-width: 16px !important;
        height: 3.2vw !important;
        max-height: 16px !important;
        padding: 0 !important; 
        margin: 0 !important; 
    }
    
    .separador-vip-platea { 
        height: 1px !important; 
        display: block !important; 
    }

    .separador-vip-platea::after {
        content: "" !important;
        position: absolute !important;
        left: 0 !important;
        margin-top: 0px !important; 
        width: 100% !important; 
        border-top: 1px solid #555555 !important; 
        z-index: 99 !important;
    }
    
    .separador-platea-mezzanine { 
        height: 12px !important; 
        display: block !important; 
    }

    .separador-platea-mezzanine::after {
        content: "" !important;
        position: absolute !important;
        left: 0 !important;
        margin-top: 6px !important; 
        width: 100% !important; 
        border-top: 0.5px solid #555555 !important; 
        z-index: 99 !important;
    }
    
    /* ESCENARIO TOTALMENTE CENTRADO */
    .escenario { 
        background-color: #34495E !important; 
        color: white !important; 
        display: flex !important;
        justify-content: center !important; 
        align-items: center !important;  
        text-align: center !important; 
        padding: 0 !important; 
        font-weight: bold !important; 
        font-size: 2.2vw !important; 
        border-radius: 4px !important; 
        margin-bottom: 8px !important; 
        letter-spacing: 2px !important; 
        width: 100% !important; 
        height: 40px !important; 
    }
    
    .texto-vertical { 
        writing-mode: vertical-rl !important; 
        text-combine-upright: none !important; 
        letter-spacing: 2px !important; 
        font-weight: bold !important; 
        font-size: 1.5vw !important; 
        text-align: center !important; 
        color: var(--text-color) !important; 
        opacity: 0.85 !important; 
        display: flex !important; 
        align-items: center !important; 
        justify-content: center !important; 
        width: 100% !important; 
        text-transform: uppercase !important; 
    }
    
    .col-disponible { background-color: #2ECC71 !important; } 
    .col-ocupado { background-color: #E74C3C !important; }    
    .col-reservado { background-color: #F1C40F !important; color: #333 !important; } 
    .col-bloqueado { background-color: #7F8C8D !important; }

    @media (min-width: 768px) {
        .label-fila { font-size: 11px !important; }
        .label-fila-derecha { font-size: 11px !important; }
        .asiento-link { font-size: 10px !important; line-height: 14px !important; }
        .texto-vertical { font-size: 12px !important; }
        .escenario { font-size: 13px !important; }
    }
    
    </style>"""

    # --- CONSTRUCCIÓN DEL HTML ---
    html_mapa = css_estilos 
    # Se eliminaron los espacios en blanco innecesarios aquí:
    html_mapa += '<div class="titulo-principal"><h3>JARDÍN DE MELODIAS</h3></div>'
    html_mapa += '<div class="contenedor-maestro-mapa">'
    html_mapa += '<div class="escenario">ESCENARIO</div>'
    
    # --- PANTALLA LAYOUT PRINCIPAL ---
    html_mapa += '<div class="pantalla-layout">'
    
    html_mapa += '<div class="zonas-lateral" style="margin-right: 6px !important;">'
    html_mapa += '<div class="texto-vertical" style="flex-grow: 7; flex-basis: 0;">VIP</div>'
    html_mapa += '<div class="texto-vertical" style="flex-grow: 7; flex-basis: 0;">PLATEA</div>'
    html_mapa += '<div class="texto-vertical" style="flex-grow: 4; flex-basis: 0; margin-top: 6px;">MEZZANINE</div>'
    html_mapa += '</div>'
    
    html_mapa += '<div class="mapa-seccion"><div class="mapa-contenedor">'
    
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
            
        html_mapa += f'<div class="label-fila-derecha">F{f}</div></div>'
        
        if f == 7:
            html_mapa += '<div class="separador-vip-platea"></div>'
            
        if f == 14:
            html_mapa += '<div class="separador-platea-mezzanine"></div>'

    df_mezz = df[df['Zona'] == 'MEZZANINE']
    if not df_mezz.empty:
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
                            
            html_mapa += f'<div class="label-fila-derecha">M-F{f}</div></div>'

    html_mapa += '</div></div>'
    
    html_mapa += '<div class="zonas-lateral" style="margin-left: 6px !important; margin-right: 0px !important;">'
    html_mapa += '<div class="texto-vertical" style="flex-grow: 7; flex-basis: 0;">VIP</div>'
    html_mapa += '<div class="texto-vertical" style="flex-grow: 7; flex-basis: 0;">PLATEA</div>'
    html_mapa += '<div class="texto-vertical" style="flex-grow: 4; flex-basis: 0; margin-top: 6px;">MEZZANINE</div>'
    html_mapa += '</div>' 
    
    html_mapa += '</div></div><br>'
    
    st.markdown(html_mapa, unsafe_allow_html=True)



   # =========================================================================
    # 💡 CONTADORES EN CASMADA: FORMATO DIRECTO (SIN VARIABLES TEXTUALES)
    # =========================================================================
    df['Estado_Clean'] = df['Estado'].astype(str).str.strip()
    
    t_disp = len(df[df['Estado_Clean'] == "Disponible"])
    t_ocup = len(df[df['Estado_Clean'] == "Ocupado"])
    t_rese = len(df[df['Estado_Clean'] == "Reservado"])
    t_bloq = len(df[df['Estado_Clean'] == "Bloqueado"])
    
    st.markdown("<hr style='margin: 20px 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    # Inyectamos el HTML directo dividiendo las partes para que Python no se confunda
    st.markdown(
        '<div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%; gap: 10px; text-align: center;">'
            '<div style="flex: 1;">'
                '<div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 4px;">'
                    '<span class="circulo-color col-disponible"></span>'
                    '<b style="font-size: 0.7rem;">Disponibles</b>'
                '</div>'
                '<div style="font-size: 1.4rem; font-weight: 700; color: #2ECC71;">' + str(t_disp) + '</div>'
            '</div>'
            '<div style="flex: 1;">'
                '<div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 4px;">'
                    '<span class="circulo-color col-ocupado"></span>'
                    '<b style="font-size: 0.7rem;">Ocupados</b>'
                '</div>'
                '<div style="font-size: 1.4rem; font-weight: 700; color: #E74C3C;">' + str(t_ocup) + '</div>'
            '</div>'
            '<div style="flex: 1;">'
                '<div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 4px;">'
                    '<span class="circulo-color col-reservado"></span>'
                    '<b style="font-size: 0.7rem;">Reservados</b>'
                '</div>'
                '<div style="font-size: 1.4rem; font-weight: 700; color: #F1C40F;">' + str(t_rese) + '</div>'
            '</div>'
            '<div style="flex: 1;">'
                '<div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 4px;">'
                    '<span class="circulo-color col-bloqueado"></span>'
                    '<b style="font-size: 0.7rem;">Bloqueados</b>'
                '</div>'
                '<div style="font-size: 1.4rem; font-weight: 700; color: #7F8C8D;">' + str(t_bloq) + '</div>'
            '</div>'
        '</div>', 
        unsafe_allow_html=True
    )
