import streamlit as st
from supabase import create_client
import random
import string
import urllib.parse
import json

st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽", layout="wide")

# =====================================================
# 🔌 CONEXIÓN Y ESTADO DE NAVEGACIÓN
# =====================================================
@st.cache_resource
def init_connection():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_connection()

# Estados críticos para que los botones funcionen
if "vista_actual" not in st.session_state: st.session_state.vista_actual = "🏟️ Grupos"
if "grupo_seleccionado" not in st.session_state: st.session_state.grupo_seleccionado = None

def ir_a(vista, grupo_id=None):
    st.session_state.vista_actual = vista
    if grupo_id:
        st.session_state.grupo_seleccionado = grupo_id
    st.rerun()

# =====================================================
# 🔐 AUTH (Sin cambios)
# =====================================================
if "user" not in st.session_state: st.session_state.user = None
def manejar_oauth():
    query_params = st.query_params
    if "code" in query_params:
        try:
            supabase.auth.exchange_code_for_session({"auth_code": query_params["code"]})
            session = supabase.auth.get_session()
            if session and session.user: st.session_state.user = session.user
            st.query_params.clear()
            st.rerun()
        except: pass

manejar_oauth()
if not st.session_state.user:
    st.title("⚽ Fulbacho Pro")
    if st.button("Iniciar sesión con Google", type="primary"):
        response = supabase.auth.sign_in_with_oauth({"provider": "google", "options": {"redirect_to": "https://fulbacho.streamlit.app"}})
        st.link_button("👉 Continuar", response.url)
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
# 🏟️ VISTA GRUPOS (CON BOTONES QUE FUNCIONAN)
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
                    st.write(f"{EMOJIS_COLORES.get(meta.get('color_a'), '⚪')} vs {EMOJIS_COLORES.get(meta.get('color_b'), '⚫')}")
                    
                    if item['rol'] == 'admin':
                        c1, c2 = st.columns(2)
                        # AQUÍ LA MAGIA: Llamamos a la función ir_a
                        if c1.button(f"⚙️ Gestionar", key=f"adm_{g['id']}", use_container_width=True):
                            ir_a("⚙️ Admin", g['id'])
                        if c2.button(f"📅 Armar Fecha", key=f"part_{g['id']}", use_container_width=True):
                            ir_a("📅 Partidos", g['id'])
                    else:
                        st.caption(f"Código: {g['codigo_invitacion']}")

# =====================================================
# ⚙️ VISTA ADMIN (CON PRE-SELECCIÓN)
# =====================================================
def vista_admin():
    st.header("⚙️ Gestión de Grupo")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data:
        st.warning("No sos administrador.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    idx = 0
    if st.session_state.grupo_seleccionado in opciones:
        idx = list(opciones.keys()).index(st.session_state.grupo_seleccionado)
    
    g_sel = st.selectbox("Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx)
    grupo_actual = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)
    
    t1, t2, t3 = st.tabs(["👥 Miembros", "➕ Invitados", "🎨 Config"])
    miembros = supabase.table("grupo_miembros").select("rol, usuarios(nombre)").eq("grupo_id", g_sel).execute().data
    with t1:
        for m in miembros: st.write(f"• **{m['usuarios']['nombre']}** ({m['rol']})")
    with t2:
        with st.form("inv", clear_on_submit=True):
            n = st.text_input("Nombre")
            if st.form_submit_button("Agregar"):
                res = supabase.table("usuarios").insert({"nombre": n}).execute()
                if res.data:
                    supabase.table("grupo_miembros").insert({"grupo_id": g_sel, "usuario_id": res.data[0]['id'], "rol": "invitado"}).execute()
                    st.rerun()
    with t3:
        meta = obtener_meta(grupo_actual)
        c1, c2 = st.columns(2)
        new_a = c1.selectbox("Color A", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta.get('color_a', 'Blanco')))
        new_b = c2.selectbox("Color B", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta.get('color_b', 'Negro')))
        if st.button("Guardar"):
            meta['color_a'], meta['color_b'] = new_a, new_b
            supabase.table("grupos").update({"tipo_cancha": json.dumps(meta)}).eq("id", g_sel).execute()
            st.success("¡Guardado!")

# =====================================================
# 📅 VISTA PARTIDOS (CON PRE-SELECCIÓN)
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

    g_sel = st.selectbox("Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx, key="psel_final")
    grupo_info = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)
    meta = obtener_meta(grupo_info)
    
    res_m = supabase.table("grupo_miembros").select("usuarios(id, nombre)").eq("grupo_id", g_sel).execute()
    j_disp = [m['usuarios'] for m in res_m.data if m['usuarios']]
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("🙋‍♂️ Convocados")
        # Función para seleccionar todos
        if f"check_all_{g_sel}" not in st.session_state: st.session_state[f"check_all_{g_sel}"] = False
        
        def toggle_all():
            for j in j_disp: st.session_state[f"c{j['id']}"] = st.session_state[f"check_all_{g_sel}"]
        
        st.checkbox("✅ Todos", key=f"check_all_{g_sel}", on_change=toggle_all)
        conv = [j for j in j_disp if st.checkbox(j['nombre'], key=f"c{j['id']}")]
    
    with col2:
        if len(conv) >= 2:
            niv = {c['id']: st.slider(f"{c['nombre']}", 1, 10, 5, key=f"l{c['id']}") for c in conv}
            if st.button("🪄 Armar Equipos", type="primary"):
                orden = sorted(conv, key=lambda x: niv[x['id']], reverse=True)
                ea, eb = [], []
                for i, jug in enumerate(orden): (ea if i % 2 == 0 else eb).append(jug)
                
                c1, c2 = st.columns(2)
                c1.success(f"{EMOJIS_COLORES.get(meta['color_a'])} EQUIPO A")
                for x in ea: c1.write(f"• {x['nombre']}")
                c2.error(f"{EMOJIS_COLORES.get(meta['color_b'])} EQUIPO B")
                for x in eb: c2.write(f"• {x['nombre']}")

# =====================================================
# 📝 PERFIL
# =====================================================
def vista_perfil():
    st.header("📝 Mi Perfil")
    u_data = supabase.table("usuarios").select("*").eq("id", user.id).single().execute().data
    nombre = st.text_input("Nombre", value=u_data['nombre'])
    if st.button("Guardar Perfil"):
        supabase.table("usuarios").update({"nombre": nombre}).eq("id", user.id).execute()
        st.success("¡Listo!")

# =====================================================
# 🎛️ NAVEGACIÓN PRINCIPAL (REEMPLAZA TABS)
# =====================================================
vistas = ["🏟️ Grupos", "📝 Perfil", "⚙️ Admin", "📅 Partidos"]

# Sidebar para cerrar sesión
if st.sidebar.button("Cerrar Sesión"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# Menú de navegación horizontal superior
# Buscamos el índice de la vista actual para que el radio button se mueva solo
idx_nav = vistas.index(st.session_state.vista_actual)
seleccion = st.radio("Navegación", vistas, index=idx_nav, horizontal=True, label_visibility="collapsed")

# Si el usuario hace clic manualmente en el radio, actualizamos el estado
if seleccion != st.session_state.vista_actual:
    st.session_state.vista_actual = seleccion
    st.rerun()

# Renderizado de la vista según el estado
if st.session_state.vista_actual == "🏟️ Grupos": vista_grupos()
elif st.session_state.vista_actual == "📝 Perfil": vista_perfil()
elif st.session_state.vista_actual == "⚙️ Admin": vista_admin()
elif st.session_state.vista_actual == "📅 Partidos": vista_partidos()
