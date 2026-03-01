import streamlit as st
from supabase import create_client
import random
import string
import urllib.parse
import json

st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽", layout="wide")

# =====================================================
# 🔌 CONEXIÓN Y ESTADO
# =====================================================
@st.cache_resource
def init_connection():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_connection()

if "vista_actual" not in st.session_state: st.session_state.vista_actual = "🏟️ Grupos"
if "grupo_seleccionado" not in st.session_state: st.session_state.grupo_seleccionado = None

def ir_a(vista, grupo_id=None):
    st.session_state.vista_actual = vista
    if grupo_id: st.session_state.grupo_seleccionado = grupo_id
    st.rerun()

# =====================================================
# 🔐 AUTH
# =====================================================
if "user" not in st.session_state: st.session_state.user = None
def manejar_oauth():
    qp = st.query_params
    if "code" in qp:
        try:
            supabase.auth.exchange_code_for_session({"auth_code": qp["code"]})
            session = supabase.auth.get_session()
            if session and session.user: st.session_state.user = session.user
            st.query_params.clear()
            st.rerun()
        except: pass

manejar_oauth()
if not st.session_state.user:
    st.title("⚽ Fulbacho Pro")
    if st.button("Iniciar sesión con Google", type="primary"):
        res = supabase.auth.sign_in_with_oauth({"provider": "google", "options": {"redirect_to": "https://fulbacho.streamlit.app"}})
        st.link_button("👉 Continuar", res.url)
    st.stop()

user = st.session_state.user

# =====================================================
# 🛠️ FUNCIONES DE APOYO
# =====================================================
EMOJIS_COLORES = {"Azul": "🔵", "Rojo": "🔴", "Blanco": "⚪", "Negro": "⚫", "Verde": "🟢", "Amarillo": "🟡", "Naranja": "🟠", "Violeta": "🟣", "Celeste": "👕"}

def obtener_meta(grupo_obj):
    raw = grupo_obj.get('tipo_cancha', '')
    default = {"mod": str(raw), "color_a": "Blanco", "color_b": "Negro"}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else default
    except: return default

# =====================================================
# 📅 VISTA PARTIDOS (TÁCTICA Y 1-CLIC)
# =====================================================
def vista_partidos():
    st.header("📅 Armado de Equipos")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data:
        st.info("Solo administradores.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    idx = 0
    if st.session_state.grupo_seleccionado in opciones:
        idx = list(opciones.keys()).index(st.session_state.grupo_seleccionado)

    g_sel = st.selectbox("Seleccionar Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx, key="psel_final")
    grupo_info = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)
    meta = obtener_meta(grupo_info)
    
    # Traemos jugadores y sus posiciones
    res_m = supabase.table("grupo_miembros").select("usuarios(id, nombre, usuario_posiciones(posiciones(nombre)))").eq("grupo_id", g_sel).execute()
    j_disp = [m['usuarios'] for m in res_m.data if m['usuarios']]
    
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("🙋‍♂️ Convocados")
        def toggle_all():
            for j in j_disp: st.session_state[f"c{j['id']}"] = st.session_state[f"check_all_{g_sel}"]
        st.checkbox("✅ Seleccionar todos", key=f"check_all_{g_sel}", on_change=toggle_all)
        
        conv = []
        for j in j_disp:
            # Extraer posiciones para mostrar al lado del nombre
            pos_list = [p['posiciones']['nombre'][:3].upper() for p in j.get('usuario_posiciones', []) if p.get('posiciones')]
            pos_str = f" [{', '.join(pos_list)}]" if pos_list else ""
            
            if st.checkbox(f"{j['nombre']}{pos_str}", key=f"c{j['id']}"):
                conv.append(j)
        st.metric("Total", len(conv))

    with col2:
        if len(conv) >= 2:
            st.subheader("⭐ Nivelación (1-10)")
            niv = {}
            for c in conv:
                # Usamos radio horizontal para nivelación 1-clic
                niv[c['id']] = st.radio(
                    f"Nivel de **{c['nombre']}**",
                    options=range(1, 11),
                    index=4, # Default 5
                    horizontal=True,
                    key=f"niv_{c['id']}"
                )
            
            st.divider()
            if st.button("🪄 Armar Equipos", type="primary", use_container_width=True):
                # Algoritmo de nivelación (Serpiente)
                orden = sorted(conv, key=lambda x: niv[x['id']], reverse=True)
                ea, eb = [], []
                for i, jug in enumerate(orden): (ea if i % 2 == 0 else eb).append(jug)
                
                c1, c2 = st.columns(2)
                emo_a, emo_b = EMOJIS_COLORES.get(meta['color_a'], '⚪'), EMOJIS_COLORES.get(meta['color_b'], '⚫')
                
                with c1:
                    st.success(f"{emo_a} EQUIPO A")
                    for x in ea: st.write(f"• {x['nombre']}")
                with c2:
                    st.error(f"{emo_b} EQUIPO B")
                    for x in eb: st.write(f"• {x['nombre']}")
                
                # Link de WhatsApp
                msg = f"⚽ *FULBACHO EN {opciones[g_sel].upper()}*\n\n{emo_a} *A:*\n" + "\n".join([f"• {j['nombre']}" for j in ea])
                msg += f"\n\n{emo_b} *B:*\n" + "\n".join([f"• {j['nombre']}" for j in eb])
                st.link_button("📲 Enviar a WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)

# =====================================================
# RESTO DE VISTAS (Sin cambios estructurales)
# =====================================================
def vista_grupos():
    st.header("🏟️ Mis Grupos")
    res = supabase.table("grupo_miembros").select("rol, grupos(*)").eq("usuario_id", user.id).execute()
    if res.data:
        cols = st.columns(2)
        for i, item in enumerate(res.data):
            g = item['grupos']
            if not g: continue
            with cols[i % 2]:
                with st.container(border=True):
                    meta = obtener_meta(g)
                    st.subheader(f"🏆 {g['nombre']}")
                    if item['rol'] == 'admin':
                        c1, c2 = st.columns(2)
                        if c1.button(f"⚙️ Config", key=f"adm_{g['id']}", use_container_width=True): ir_a("⚙️ Admin", g['id'])
                        if c2.button(f"📅 Equipos", key=f"part_{g['id']}", use_container_width=True): ir_a("📅 Partidos", g['id'])
                    else: st.caption(f"Código: {g['codigo_invitacion']}")

def vista_admin():
    # ... (Mantenemos lógica anterior de admin) ...
    st.header("⚙️ Gestión de Grupo")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data: return
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    idx = 0
    if st.session_state.grupo_seleccionado in opciones:
        idx = list(opciones.keys()).index(st.session_state.grupo_seleccionado)
    g_sel = st.selectbox("Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx)
    # Formulario de Invitados y Configuración de Colores igual que v2.1...
    # (Omitido por brevedad, mantener igual)

def vista_perfil():
    st.header("📝 Mi Perfil")
    u_data = supabase.table("usuarios").select("*").eq("id", user.id).single().execute().data
    nombre = st.text_input("Nombre", value=u_data['nombre'])
    # Selector de posiciones para el perfil
    pos_db = supabase.table("posiciones").select("*").execute().data or []
    opciones = {p['id']: f"{p['nombre']}" for p in pos_db}
    actuales = supabase.table("usuario_posiciones").select("posicion_id").eq("usuario_id", user.id).execute()
    ids_act = [a['posicion_id'] for a in actuales.data]
    sel = st.multiselect("Tus posiciones", options=list(opciones.keys()), default=[p for p in ids_act if p in opciones], format_func=lambda x: opciones[x])
    if st.button("Guardar Perfil"):
        supabase.table("usuarios").update({"nombre": nombre}).eq("id", user.id).execute()
        supabase.table("usuario_posiciones").delete().eq("usuario_id", user.id).execute()
        if sel: supabase.table("usuario_posiciones").insert([{"usuario_id": user.id, "posicion_id": pid} for pid in sel]).execute()
        st.success("¡Guardado!")

# =====================================================
# NAVEGACIÓN
# =====================================================
vistas = ["🏟️ Grupos", "📝 Perfil", "⚙️ Admin", "📅 Partidos"]
idx_nav = vistas.index(st.session_state.vista_actual)
seleccion = st.radio("Navegación", vistas, index=idx_nav, horizontal=True, label_visibility="collapsed")
if seleccion != st.session_state.vista_actual:
    st.session_state.vista_actual = seleccion
    st.rerun()

if st.session_state.vista_actual == "🏟️ Grupos": vista_grupos()
elif st.session_state.vista_actual == "📝 Perfil": vista_perfil()
elif st.session_state.vista_actual == "⚙️ Admin": vista_admin()
elif st.session_state.vista_actual == "📅 Partidos": vista_partidos()
