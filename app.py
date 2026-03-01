import streamlit as st
from supabase import create_client
import random
import string
import urllib.parse
import json

st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽", layout="wide")

# =====================================================
# 🔌 CONEXIÓN
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
# 🛠️ UTILIDADES
# =====================================================
EMOJIS_COLORES = {"Azul": "🔵", "Rojo": "🔴", "Blanco": "⚪", "Negro": "⚫", "Verde": "🟢", "Amarillo": "🟡", "Naranja": "🟠", "Violeta": "🟣", "Celeste": "👕"}

def obtener_meta(grupo_obj):
    raw = grupo_obj.get('tipo_cancha', '')
    default = {"mod": "Fútbol", "color_a": "Blanco", "color_b": "Negro"}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else default
    except: return default

# =====================================================
# 🏟️ VISTA GRUPOS
# =====================================================
def vista_grupos():
    st.header("🏟️ Mis Grupos")
    try:
        res = supabase.table("grupo_miembros").select("rol, grupos(*)").eq("usuario_id", user.id).execute()
        if res.data:
            cols = st.columns(2)
            for i, item in enumerate(res.data):
                g = item.get('grupos')
                if not g: continue
                with cols[i % 2]:
                    with st.container(border=True):
                        meta = obtener_meta(g)
                        st.subheader(f"🏆 {g['nombre']}")
                        st.write(f"{EMOJIS_COLORES.get(meta.get('color_a'), '⚪')} vs {EMOJIS_COLORES.get(meta.get('color_b'), '⚫')}")
                        if item['rol'] == 'admin':
                            c1, c2 = st.columns(2)
                            if c1.button(f"⚙️ Config", key=f"adm_{g['id']}", use_container_width=True): ir_a("⚙️ Admin", g['id'])
                            if c2.button(f"📅 Equipos", key=f"part_{g['id']}", use_container_width=True): ir_a("📅 Partidos", g['id'])
                        else:
                            st.caption(f"Modalidad: {meta.get('mod')} | Código: {g['codigo_invitacion']}")
        else:
            st.info("No tenés grupos. ¡Creá uno abajo!")
    except Exception as e:
        st.error(f"Error cargando grupos: {e}")

    st.divider()
    with st.expander("➕ Crear o Unirse a un Grupo"):
        c1, c2 = st.columns(2)
        with c1:
            with st.form("crear_g"):
                n = st.text_input("Nombre del Grupo")
                if st.form_submit_button("Crear"):
                    if n:
                        cod = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                        meta_init = json.dumps({"mod": "F5", "color_a": "Blanco", "color_b": "Negro"})
                        new = supabase.table("grupos").insert({"nombre": n, "tipo_cancha": meta_init, "codigo_invitacion": cod}).execute()
                        if new.data:
                            supabase.table("grupo_miembros").insert({"grupo_id": new.data[0]['id'], "usuario_id": user.id, "rol": "admin"}).execute()
                            st.rerun()
        with c2:
            with st.form("unir_g"):
                cod_in = st.text_input("Código de Invitación")
                if st.form_submit_button("Unirse"):
                    g_res = supabase.table("grupos").select("id").eq("codigo_invitacion", cod_in).execute()
                    if g_res.data:
                        supabase.table("grupo_miembros").upsert({"grupo_id": g_res.data[0]['id'], "usuario_id": user.id, "rol": "miembro"}).execute()
                        st.rerun()

# =====================================================
# 📅 VISTA PARTIDOS (FIXED)
# =====================================================
def vista_partidos():
    st.header("📅 Armado de Equipos")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    
    if not admin_g.data:
        st.info("Solo para administradores.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    idx = 0
    if st.session_state.grupo_seleccionado in opciones:
        idx = list(opciones.keys()).index(st.session_state.grupo_seleccionado)

    g_sel = st.selectbox("Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx, key="psel_main")
    grupo_info = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)
    meta = obtener_meta(grupo_info)
    
    # Traemos jugadores de forma simple para evitar errores de relación
    res_m = supabase.table("grupo_miembros").select("usuarios(id, nombre)").eq("grupo_id", g_sel).execute()
    j_disp = [m['usuarios'] for m in res_m.data if m['usuarios']]
    
    col_lista, col_nivel = st.columns([1, 1.5])
    
    convocados = []
    with col_lista:
        st.subheader("🙋‍♂️ ¿Quiénes juegan?")
        if f"all_{g_sel}" not in st.session_state: st.session_state[f"all_{g_sel}"] = False
        def toggle():
            for j in j_disp: st.session_state[f"c{j['id']}"] = st.session_state[f"all_{g_sel}"]
        
        st.checkbox("Seleccionar todos", key=f"all_{g_sel}", on_change=toggle)
        for j in j_disp:
            if st.checkbox(j['nombre'], key=f"c{j['id']}"):
                convocados.append(j)

    with col_nivel:
        if convocados:
            st.subheader("⭐ Nivelación rápida")
            niv = {}
            for c in convocados:
                niv[c['id']] = st.radio(f"Nivel de **{c['nombre']}**", options=range(1,11), index=4, horizontal=True, key=f"n_{c['id']}")
            
            st.divider()
            if st.button("🪄 Armar Equipos Equilibrados", type="primary", use_container_width=True):
                orden = sorted(convocados, key=lambda x: niv[x['id']], reverse=True)
                ea, eb = [], []
                for i, jug in enumerate(orden): (ea if i % 2 == 0 else eb).append(jug)
                
                c1, c2 = st.columns(2)
                ea_n, eb_n = meta.get('color_a', 'A'), meta.get('color_b', 'B')
                with c1:
                    st.success(f"{EMOJIS_COLORES.get(ea_n, '⚪')} EQUIPO {ea_n.upper()}")
                    for x in ea: st.write(f"• {x['nombre']}")
                with c2:
                    st.error(f"{EMOJIS_COLORES.get(eb_n, '⚫')} EQUIPO {eb_n.upper()}")
                    for x in eb: st.write(f"• {x['nombre']}")
                
                msg = f"⚽ *EQUIPOS {opciones[g_sel].upper()}*\n\n" + f"*{ea_n.upper()}:*\n" + "\n".join([f"• {j['nombre']}" for j in ea]) + f"\n\n*{eb_n.upper()}:*\n" + "\n".join([f"• {j['nombre']}" for j in eb])
                st.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)

# =====================================================
# ⚙️ VISTA ADMIN (RESUMIDA)
# =====================================================
def vista_admin():
    st.header("⚙️ Gestión")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data: return
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    g_sel = st.selectbox("Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], key="adm_sel")
    
    t1, t2 = st.tabs(["👥 Invitados", "🎨 Colores"])
    with t1:
        with st.form("inv", clear_on_submit=True):
            n = st.text_input("Nombre Invitado")
            if st.form_submit_button("Agregar"):
                res = supabase.table("usuarios").insert({"nombre": n}).execute()
                if res.data:
                    supabase.table("grupo_miembros").insert({"grupo_id": g_sel, "usuario_id": res.data[0]['id'], "rol": "invitado"}).execute()
                    st.rerun()
    with t2:
        meta = obtener_meta(next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel))
        c1, c2 = st.columns(2)
        na = c1.selectbox("Color A", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta['color_a']))
        nb = c2.selectbox("Color B", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta['color_b']))
        if st.button("Guardar"):
            meta['color_a'], meta['color_b'] = na, nb
            supabase.table("grupos").update({"tipo_cancha": json.dumps(meta)}).eq("id", g_sel).execute()
            st.rerun()

# =====================================================
# 📝 PERFIL
# =====================================================
def vista_perfil():
    st.header("📝 Perfil")
    u_data = supabase.table("usuarios").select("*").eq("id", user.id).single().execute().data
    n = st.text_input("Nombre", value=u_data['nombre'])
    if st.button("Guardar"):
        supabase.table("usuarios").update({"nombre": n}).eq("id", user.id).execute()
        st.success("Guardado")

# =====================================================
# 🎛️ NAVEGACIÓN
# =====================================================
vistas = ["🏟️ Grupos", "📝 Perfil", "⚙️ Admin", "📅 Partidos"]
nav = st.radio("Menú", vistas, index=vistas.index(st.session_state.vista_actual), horizontal=True, label_visibility="collapsed")
if nav != st.session_state.vista_actual:
    st.session_state.vista_actual = nav
    st.rerun()

if st.session_state.vista_actual == "🏟️ Grupos": vista_grupos()
elif st.session_state.vista_actual == "📝 Perfil": vista_perfil()
elif st.session_state.vista_actual == "⚙️ Admin": vista_admin()
elif st.session_state.vista_actual == "📅 Partidos": vista_partidos()
