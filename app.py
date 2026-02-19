import streamlit as st
from supabase import create_client
import httpx

st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")

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
    supabase.auth.sign_in_with_oauth(
        {
            "provider": "google",
            "options": {
                # CAMBIAR por tu URL real cuando publiques
                "redirect_to": "http://localhost:8501"
            }
        }
    )

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
            "posiciones_preferidas": []
        }).execute()

except Exception as e:
    st.error(f"Error validando usuario: {e}")

st.title("⚽ Draft Master Pro")
st.success(f"Logueado como {user.email}")

if st.button("Cerrar sesión"):
    logout()

# -------------------------------
# CARGAR JUGADORES
# -------------------------------
jugadores = []
try:
    res = supabase.table("usuarios").select("*").execute()
    jugadores = res.data if res.data else []
except Exception as e:
    st.warning(f"No se pudo leer la tabla: {e}")

# -------------------------------
# PESTAÑAS
# -------------------------------
t1, t2, t3 = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Admin"])

# -------------------------------
# REGISTRO / EDITAR PERFIL
# -------------------------------
with t1:
    st.subheader("Editar mi perfil")

    with st.form("reg_form"):
        nombre = st.text_input("Tu nombre visible")

        pos = st.multiselect(
            "Posiciones",
            ["Arquero", "Defensor", "Mediocampista", "Delantero"]
        )

        submit = st.form_submit_button("Guardar cambios")

        if submit and nombre:

            # VALIDAR NOMBRE DUPLICADO
            check = supabase.table("usuarios")\
                .select("id")\
                .eq("nombre", nombre)\
                .neq("id", user.id)\
                .execute()

            if check.data:
                st.error("⚠️ Ese nombre ya está en uso.")
            else:
                try:
                    supabase.table("usuarios")\
                        .update({
                            "nombre": nombre,
                            "posiciones_preferidas": pos
                        })\
                        .eq("id", user.id)\
                        .execute()

                    st.success("Perfil actualizado")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# -------------------------------
# LISTADO
# -------------------------------
with t2:
    if not jugadores:
        st.write("No hay jugadores cargados todavía.")
    else:
        for j in jugadores:
            posiciones = j.get("posiciones_preferidas") or []
            st.write(f"👤 {j['nombre']} - {', '.join(posiciones)}")

# -------------------------------
# ADMIN
# -------------------------------
with t3:
    st.write(f"Total de jugadores: {len(jugadores)}")

    if st.button("Limpiar Cache de Conexión"):
        st.cache_resource.clear()
        st.rerun()
