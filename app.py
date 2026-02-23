import streamlit as st
from supabase import create_client
import random
import string

st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽")

# =====================================================
# 🔌 CONEXIÓN
# =====================================================
@st.cache_resource
def init_connection():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_connection()


# =====================================================
# 🔐 AUTH
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
            st.error(f"Error intercambiando código: {e}")


def login():
    response = supabase.auth.sign_in_with_oauth(
        {
            "provider": "google",
            "options": {
                "redirect_to": "https://fulbacho.streamlit.app"
            }
        }
    )

    st.link_button("👉 Continuar con Google", response.url)


def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()


def obtener_sesion():
    session = supabase.auth.get_session()
    if session and session.user:
        st.session_state.user = session.user


manejar_oauth()
obtener_sesion()


# =====================================================
# 🚪 LOGIN SCREEN
# =====================================================
if not st.session_state.user:
    st.title("⚽ Fulbacho Pro")
    st.subheader("Login requerido")

    if st.button("Iniciar sesión con Google"):
        login()

    st.stop()


user = st.session_state.user

# =====================================================
# 👤 CREAR USUARIO SI NO EXISTE
# =====================================================
existing = supabase.table("usuarios").select("*").eq("id", user.id).execute()

if not existing.data:
    supabase.table("usuarios").insert({
        "id": user.id,
        "nombre": user.user_metadata.get("full_name", user.email),
        "email": user.email,
        "posiciones_preferidas": []
    }).execute()


# =====================================================
# 🧱 VISTAS
# =====================================================

def vista_grupos():
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

    # Crear grupo
    st.subheader("Crear Grupo")

    with st.form("crear_grupo"):
        nombre = st.text_input("Nombre del grupo")
        tipo = st.selectbox("Tipo de cancha", ["5", "6", "7", "8", "9", "10", "11"])
        crear = st.form_submit_button("Crear")

        if crear and nombre:
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

            nuevo = supabase.table("grupos").insert({
                "nombre": nombre,
                "tipo_cancha": tipo,
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

    st.divider()

    # Unirse a grupo
with st.form("unirse_grupo"):
    codigo = st.text_input("Código de invitación")
    unirse = st.form_submit_button("Unirse")

    if unirse and codigo:
        grupo = supabase.table("grupos") \
            .select("id") \
            .eq("codigo_invitacion", codigo) \
            .execute()

        if not grupo.data:
            st.error("Código inválido")
        else:
            grupo_id = grupo.data[0]["id"]

            # verificar si ya pertenece
            existe = supabase.table("grupo_miembros") \
                .select("*") \
                .eq("grupo_id", grupo_id) \
                .eq("usuario_id", user.id) \
                .execute()

            if existe.data:
                st.warning("Ya pertenecés a este grupo.")
            else:
                supabase.table("grupo_miembros").insert({
                    "grupo_id": grupo_id,
                    "usuario_id": user.id,
                    "rol": "miembro"
                }).execute()

                st.success("Te uniste al grupo!")
                st.rerun()


def vista_perfil():
    st.subheader("Mi Perfil")

    datos = supabase.table("usuarios") \
        .select("*") \
        .eq("id", user.id) \
        .single() \
        .execute()

    nombre = st.text_input("Nombre", value=datos.data["nombre"])

    posiciones = st.multiselect(
        "Posiciones preferidas",
        ["Arquero", "Defensor", "Mediocampista", "Delantero"],
        default=datos.data["posiciones_preferidas"]
    )

    if st.button("Guardar cambios"):
        supabase.table("usuarios").update({
            "nombre": nombre,
            "posiciones_preferidas": posiciones
        }).eq("id", user.id).execute()

        st.success("Perfil actualizado")
        st.rerun()


def vista_jugadores():
    st.subheader("Jugadores")
    st.info("Próximamente.")


def vista_admin():
    st.subheader("Panel Admin")
    st.info("Opciones avanzadas pronto.")


# =====================================================
# 🎛️ INTERFAZ PRINCIPAL
# =====================================================
st.title("⚽ Fulbacho Pro")
st.success(f"Logueado como {user.email}")

if st.button("Cerrar sesión"):
    logout()

t0, t1, t2, t3 = st.tabs(["🏟️ Grupos", "📝 Perfil", "⭐ Jugadores", "⚙️ Admin"])

with t0:
    vista_grupos()

with t1:
    vista_perfil()

with t2:
    vista_jugadores()

with t3:
    vista_admin()
