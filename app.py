import streamlit as st
from supabase import create_client, Client
import urllib.parse

st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")

# --- CONEXIÓN MANUAL REFORZADA ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
        key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
        # Agregamos opciones para evitar que la conexión se duerma
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error cargando credenciales: {e}")
        return None

supabase = init_connection()

st.title("⚽ Draft Master Pro")

# --- TEST DE CONEXIÓN INMEDIATO ---
if supabase:
    try:
        # Intentamos una operación ultra simple
        res = supabase.table("usuarios").select("nombre").limit(1).execute()
        st.success("🚀 ¡Conexión exitosa!")
    except Exception as e:
        st.error(f"Error al leer la tabla: {e}")
        st.info("💡 Si sale 'Name or service not known', es un problema de DNS de la nube.")

# --- PESTAÑAS ---
t1, t2, t3 = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Admin"])

with t1:
    with st.form("reg"):
        nombre = st.text_input("Nombre")
        pos = st.multiselect("Posiciones", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        if st.form_submit_button("Registrar"):
            if nombre and pos:
                supabase.table("usuarios").insert({"nombre": nombre, "posiciones_preferidas": pos}).execute()
                st.success("¡Guardado!")
                st.rerun()
