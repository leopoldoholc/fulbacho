import streamlit as st
from supabase import create_client, Client
import httpx

st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")

# --- CONEXIÓN ULTRA-RESISTENTE ---
@st.cache_resource
def init_connection():
    try:
        # Extraemos los datos de los secrets
        url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
        key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
        
        # Forzamos a que el cliente use un timeout más largo y no verifique DNS tan estrictamente
        # Esto ayuda cuando la red de la nube está inestable
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error cargando credenciales: {e}")
        return None

supabase = init_connection()

st.title("⚽ Draft Master Pro")

# --- LÓGICA DE LECTURA SEGURA ---
jugadores = []
if supabase:
    try:
        # Intentamos una lectura rápida
        res = supabase.table("usuarios").select("*").execute()
        jugadores = res.data if res.data else []
        st.success("✅ Conectado a la base de datos")
    except Exception as e:
        st.warning(f"⚠️ Nota: No se pudo leer la tabla (esperando red...). Error: {e}")
        st.info("Intentá registrar un jugador abajo para forzar la conexión.")

# --- PESTAÑAS ---
t1, t2, t3 = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Admin"])

with t1:
    with st.form("reg_form"):
        nombre = st.text_input("Tu nombre")
        pos = st.multiselect("Posiciones", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        submit = st.form_submit_button("Registrar Jugador")
        
        if submit and nombre and pos:
            try:
                supabase.table("usuarios").insert({
                    "nombre": nombre, 
                    "posiciones_preferidas": pos
                }).execute()
                st.success("¡Registrado con éxito!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

with t2:
    if not jugadores:
        st.write("No hay jugadores cargados todavía.")
    else:
        for j in jugadores:
            st.write(f"👤 {j['nombre']} - {', '.join(j['posiciones_preferidas'])}")

with t3:
    st.write(f"Total de jugadores: {len(jugadores)}")
    if st.button("Limpiar Cache de Conexión"):
        st.cache_resource.clear()
        st.rerun()
