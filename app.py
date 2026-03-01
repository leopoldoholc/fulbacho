import streamlit as st
from supabase import create_client
import random
import string
import urllib.parse

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

def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# =====================================================
# 🔐 AUTH & SESSION
# =====================================================
if "user" not in st.session_state:
    st.session_state.user = None

def manejar_oauth():
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        try:
            supabase.auth.exchange_code_for_session({"auth_code": code})
            session = supabase.auth.get_session()
            if session and session.user:
                st.session_state.user = session.user
            st.query_params.clear()
            st.rerun()
        except:
            pass

def login():
    response = supabase.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {"redirect_to": "https://fulbacho.streamlit.app"}
    })
    st.link_button("👉 Continuar con Google", response.url)

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

manejar_oauth()

if not st.session_state.user:
    st.title("⚽ Fulbacho Pro")
    st.subheader("Gestión de equipos y partidos")
    if st.button("Iniciar sesión con Google", type="primary"):
        login()
    st.stop()

user = st.session_state.user

# Sync de usuario inicial
try:
    existing = supabase.table("usuarios").select("*").eq("id", user.id).execute()
    if not existing.data:
        supabase.table("usuarios").insert({
            "id": user.id,
            "nombre": user.user_metadata.get("full_name", user.email),
            "email": user.email
        }).execute()
except:
    pass

# =====================================================
# 🏟️ VISTA GRUPOS
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
                    st.subheader(g['nombre'])
                    st.caption(f"Modalidad: {g.get('tipo_cancha', 'N/A')} | Rol: {item['rol']}")
                    st.code(f"Código: {g['codigo_invitacion']}")
    else:
        st.info("Aún no sos parte de ningún grupo.")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Crear Grupo")
        with st.form("crear_g"):
            n = st.text_input("Nombre del grupo")
            res_mod = supabase.table("modalidades").select("*").execute()
            mods = {m['id']: m['nombre'] for m in res_mod.data} if res_mod.data else {1: "Fútbol 5"}
            m_id = st.selectbox("Modalidad", options=list(mods.keys()), format_func=lambda x: mods[x])
            if st.form_submit_button("Crear"):
                if n:
                    cod = generar_codigo()
                    new = supabase.table("grupos").insert({"nombre": n, "tipo_cancha": mods[m_id], "codigo_invitacion": cod}).execute()
                    if new.data:
                        supabase.table("grupo_miembros").insert({"grupo_id": new.data[0]['id'], "usuario_id": user.id, "rol": "admin"}).execute()
                        st.rerun()
    with c2:
        st.subheader("Unirse")
        with st.form("unir_g"):
            cod_in = st.text_input("Código")
            if st.form_submit_button("Unirse"):
                g_res = supabase.table("grupos").select("id").eq("codigo_invitacion", cod_in).execute()
                if g_res.data:
                    supabase.table("grupo_miembros").upsert({"grupo_id": g_res.data[0]['id'], "usuario_id": user.id, "rol": "miembro"}).execute()
                    st.rerun()

# =====================================================
# 📝 VISTA PERFIL
# =====================================================
def vista_perfil():
    st.header("📝 Mi Perfil")
    u_data = supabase.table("usuarios").select("*").eq("id", user.id).single().execute().data
    with st.container(border=True):
        nuevo_n = st.text_input("Nombre", value=u_data['nombre'])
        pos_db = supabase.table("posiciones").select("*").execute().data or []
        opciones = {p['id']: f"{p['nombre']} ({p['categoria']})" for p in pos_db}
        actuales = supabase.table("usuario_posiciones").select("posicion_id").eq("usuario_id", user.id).execute()
        ids_act = [a['posicion_id'] for a in actuales.data]
        sel = st.multiselect("Posiciones", options=list(opciones.keys()), default=[p for p in ids_act if p in opciones], format_func=lambda x: opciones[x])
        if st.button("Guardar"):
            supabase.table("usuarios").update({"nombre": nuevo_n}).eq("id", user.id).execute()
            supabase.table("usuario_posiciones").delete().eq("usuario_id", user.id).execute()
            if sel:
                supabase.table("usuario_posiciones").insert([{"usuario_id": user.id, "posicion_id": pid} for pid in sel]).execute()
            st.success("¡Guardado!")

# =====================================================
# ⚙️ VISTA ADMIN
# =====================================
def vista_admin():
    st.header("⚙️ Admin")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(nombre)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data:
        st.warning("No sos admin.")
        return
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    g_sel = st.selectbox("Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
    
    t1, t2 = st.tabs(["👥 Miembros", "➕ Invitados"])
    with t1:
        miembros = supabase.table("grupo_miembros").select("rol, usuarios(nombre, email)").eq("grupo_id", g_sel).execute()
        for m in miembros.data:
            st.write(f"• **{m['usuarios']['nombre']}** ({m['rol']})")
    with t2:
        with st.form("inv"):
            inv_n = st.text_input("Nombre Invitado")
            if st.form_submit_button("Agregar"):
                res = supabase.table("usuarios").insert({"nombre": inv_n}).execute()
                if res.data:
                    supabase.table("grupo_miembros").insert({"grupo_id": g_sel, "usuario_id": res.data[0]['id'], "rol": "invitado"}).execute()
                    st.rerun()

# =====================================================
# 📅 VISTA PARTIDOS
# =====================================================
def vista_partidos():
    st.header("📅 Armado de Equipos")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(nombre)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data:
        st.info("Sección para administradores de grupo.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    g_sel = st.selectbox("Elegí el grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], key="psel")
    
    res_m = supabase.table("grupo_miembros").select("usuarios(id, nombre)").eq("grupo_id", g_sel).execute()
    j_disp = [m['usuarios'] for m in res_m.data if m['usuarios']]
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("🙋‍♂️ ¿Quiénes juegan?")
        conv = []
        for j in j_disp:
            if st.checkbox(j['nombre'], key=f"c{j['id']}"): conv.append(j)
    
    with col2:
        if len(conv) < 2:
            st.info("Seleccioná al menos 2 pibes.")
        else:
            st.subheader("⚖️ Nivelación manual")
            niv = {}
            for c in conv:
                niv[c['id']] = st.slider(f"Nivel {c['nombre']}", 1, 10, 5, key=f"l{c['id']}")
            
            if st.button("🪄 Armar Equipos", type="primary"):
                orden = sorted(conv, key=lambda x: niv[x['id']], reverse=True)
                ea, eb = [], []
                for i, jug in enumerate(orden):
                    (ea if i % 2 == 0 else eb).append(jug)
                
                ca, cb = st.columns(2)
                ca.success("🔵 EQUIPO A")
                for x in ea: ca.write(f"🏃 {x['nombre']}")
                cb.error("🔴 EQUIPO B")
                for x in eb: cb.write(f"🏃 {x['nombre']}")
                
                msg = f"⚽ *Equipos*\n\n🔵 A:\n" + "\n".join([f"- {j['nombre']}" for j in ea])
                msg += f"\n\n🔴 B:\n" + "\n".join([f"- {j['nombre']}" for j in eb])
                st.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}")

# =====================================================
# 🎛️ MAIN
# =====================================================
st.sidebar.title("⚽ Fulbacho Pro")
if st.sidebar.button("Cerrar Sesión"): logout()

tabs = st.tabs(["🏟️ Grupos", "📝 Perfil", "⚙️ Admin", "📅 Partidos"])
with tabs[0]: vista_grupos()
with tabs[1]: vista_perfil()
with tabs[2]: vista_admin()
with tabs[3]: vista_partidos()
