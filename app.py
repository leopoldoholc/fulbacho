import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽")

# -------------------------------
# CONEXIÓN
# -------------------------------
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
        key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error cargando credenciales: {e}")
        return None

supabase = init_connection()

# -------------------------------
# LOGIN GOOGLE
# -------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login():
    try:
        response = supabase.auth.sign_in_with_oauth(
            {
                "provider": "google",
                "options": {
                    "redirect_to": "https://fulbacho.streamlit.app"
                }
            }
        )

        auth_url = response.url  # <-- acá está la diferencia

        st.markdown(f"[Click acá si no redirige automáticamente]({auth_url})")

        st.components.v1.html(
            f"""
            <script>
                window.location.href = "{auth_url}";
            </script>
            """,
            height=0,
        )

    except Exception as e:
        st.error(f"Error en login: {e}")


def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# Detectar sesión activa
if supabase:
    session = supabase.auth.get_session()
    if session and session.user:
        st.session_state.user = session.user

# -------------------------------
# SI NO ESTÁ LOGUEADO
# -------------------------------
if not st.session_state.user:
    st.title("⚽ Draft Master Pro")
    st.subheader("Login requerido")
    if st.button("Iniciar sesión con Google"):
        login()
    st.stop()

# -------------------------------
# USUARIO LOGUEADO
# -------------------------------
user = st.session_state.user

# Crear registro en tabla usuarios si no existe
try:
    existing = supabase.table("usuarios").select("*").eq("id", user.id).execute()

    if not existing.data:
        supabase.table("usuarios").insert({
            "id": user.id,
            "nombre": user.user_metadata.get("full_name", user.email),
            "email": user.email,
            "posiciones_preferidas": []
        }).execute()
except Exception as e:
    st.error(f"Error validando usuario: {e}")

st.title("⚽ Fulbacho Pro")
st.success(f"Logueado como {user.email}")

if st.button("Cerrar sesión"):
    logout()

# -------------------------------
# PESTAÑAS
# -------------------------------
t0, t1, t2, t3 = st.tabs(["🏟️ Grupos", "📝 Perfil", "⭐ Jugadores", "⚙️ Admin"])

# =====================================================
# 🏟️ GRUPOS
# =====================================================
with t0:
    st.subheader("Mis Grupos")

    membresias = supabase.table("grupo_miembros") \
        .select("grupo_id, rol") \
        .eq("usuario_id", user.id) \
        .execute()

    grupos_usuario = []

    if membresias.data:
        for m in membresias.data:
            grupo = supabase.table("grupos") \
                .select("*") \
                .eq("id", m["grupo_id"]) \
                .single() \
                .execute()

            if grupo.data:
                grupos_usuario.append({
                    "nombre": grupo.data["nombre"],
                    "codigo": grupo.data["codigo_invitacion"],
                    "rol": m["rol"]
                })

    if grupos_usuario:
        for g in grupos_usuario:
            st.write(f"🏆 {g['nombre']} | Código: {g['codigo']} | Rol: {g['rol']}")
    else:
        st.info("Todavía no pertenecés a ningún grupo.")

    st.divider()

    # CREAR GRUPO
    st.subheader("Crear Grupo")

    with st.form("crear_grupo"):
        nombre_grupo = st.text_input("Nombre del grupo")
        tipo_cancha = st.selectbox(
            "Tipo de cancha",
            ["5", "6", "7", "8", "9", "10", "11"]
        )

        crear = st.form_submit_button("Crear")

        if crear and nombre_grupo:
            try:
                codigo = supabase.rpc("generar_codigo_invitacion").execute().data

                nuevo = supabase.table("grupos").insert({
                    "nombre": nombre_grupo,
                    "tipo_cancha": tipo_cancha,
                    "codigo_invitacion": codigo
                }).execute()

                grupo_id = nuevo.data[0]["id"]

                supabase.table("grupo_miembros").insert({
                    "grupo_id": grupo_id,
                    "usuario_id": user.id,
                    "rol": "admin"
                }).execute()

                st.success(f"Grupo creado! Código: {codigo}")
                st.rerun()

            except Exception as e:
                st.error(f"Error creando grupo: {e}")

    st.divider()

    # UNIRSE A GRUPO
    st.subheader("Unirse a Grupo")

    with st.form("unirse_grupo"):
        codigo_input = st.text_input("Código de invitación").upper()
        unirse = st.form_su_


