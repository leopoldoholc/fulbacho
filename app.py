import streamlit as st
from supabase import create_client
import random
import string
import urllib.parse

st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽", layout="wide")

# =====================================================
# 🔌 CONEXIÓN Y UTILIDADES
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
# 🔐 AUTHENTICATION
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
        except Exception as e:
            st.error(f"Error en Auth: {e}")

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
    st.subheader("Bienvenido al gestor de partidos definitivo")
    if st.button("Iniciar sesión con Google", type="primary"):
        login()
    st.stop()

user = st.session_state.user

# =====================================================
# 👤 SYNC USUARIO (Asegurar que exista en la tabla pública)
# =====================================================
existing = supabase.table("usuarios").select("*").eq("id", user.id).execute()
if not existing.data:
    supabase.table("usuarios").insert({
        "id": user.id,
        "nombre": user.user_metadata.get("full_name", user.email),
        "email": user.email
    }).execute()

# =====================================================
# 🏟️ VISTA GRUPOS
# =====================================================
def vista_grupos():
    st.header("🏟️ Mis Grupos")
    
    # Listar grupos actuales
    res = supabase.table("grupo_miembros").select("rol, grupos(*)").eq("usuario_id", user.id).execute()
    
    if res.data:
        cols = st.columns(2)
        for i, item in enumerate(res.data):
            g = item['grupos']
            with cols[i % 2]:
                with st.container(border=True):
                    st.subheader(g['nombre'])
                    st.caption(f"Modalidad: {g.get('tipo_cancha', 'N/A')} | Rol: {item['rol']}")
                    st.code(f"Código: {g['codigo_invitacion']}")
    else:
        st.info("Aún no sos parte de ningún grupo.")

    st.divider()
    
    col_c, col_u = st.columns(2)
    
    with col_c:
        st.subheader("Crear Grupo")
        with st.form("form_crear"):
            nombre_g = st.text_input("Nombre del equipo/grupo")
            res_mod = supabase.table("modalidades").select("*").execute()
            mods = {m['id']: m['nombre'] for m in res_mod.data} if res_mod.data else {1: "Fútbol 5"}
            mod_sel = st.selectbox("Modalidad", options=list(mods.keys()), format_func=lambda x: mods[x])
            
            if st.form_submit_button("Crear Grupo", use_container_width=True):
                codigo = generar_codigo()
                nuevo = supabase.table("grupos").insert({
                    "nombre": nombre_g,
                    "tipo_cancha": mods[mod_sel],
                    "codigo_invitacion": codigo
                }).execute()
                
                if nuevo.data:
                    supabase.table("grupo_miembros").insert({
                        "grupo_id": nuevo.data[0]['id'],
                        "usuario_id": user.id,
                        "rol": "admin"
                    }).execute()
                    st.success("¡Grupo creado!")
                    st.rerun()

    with col_u:
        st.subheader("Unirse a Grupo")
        with st.form("form_unirse"):
            cod_input = st.text_input("Ingresá el código de 6 dígitos")
            if st.form_submit_button("Unirse
