import streamlit as st
from st_supabase_connection import SupabaseConnection
import urllib.parse

st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")

# --- CONEXIÓN OFICIAL ---
@st.cache_resource(ttl=60) # Cache de 1 minuto para no saturar
def get_conn():
    try:
        return st.connection("supabase", type=SupabaseConnection)
    except:
        return None

conn = get_conn()

st.title("⚽ Draft Master Pro")

# --- LECTURA DE DATOS ---
jugadores = []
if conn:
    try:
        res = conn.table("usuarios").select("*").execute()
        jugadores = res.data if res.data else []
    except Exception as e:
        st.error(f"Error de red o tabla: {e}")

# --- DEFINIMOS LAS PESTAÑAS (Aquí estaba el NameError) ---
tab_reg, tab_vot, tab_admin = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Armar Equipos"])

with tab_reg:
    st.header("Nuevo Jugador")
    with st.form("registro_form"):
        nom = st.text_input("Nombre Completo")
        # Tu campo en Supabase es un ARRAY, así que mandamos una lista
        pos = st.multiselect("Posiciones", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        
        if st.form_submit_button("Registrar"):
            if nom and pos and conn:
                try:
                    conn.table("usuarios").insert({
                        "nombre": nom,
                        "posiciones_preferidas": pos
                    }).execute()
                    st.success("¡Registrado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo guardar: {e}")

with tab_vot:
    st.header("Nivel de los Pibes")
    if not jugadores:
        st.info("No hay jugadores para calificar.")
    else:
        for j in jugadores:
            # Manejamos el array de posiciones para mostrarlo lindo
            p_list = j.get('posiciones_preferidas', [])
            p_str = ", ".join(p_list) if p_list else "Sin posición"
            
            with st.expander(f"⭐ {j['nombre']} ({p_str})"):
                st.write("Para calificar, agregá la columna 'nivel' en Supabase.")

with tab_admin:
    st.header("Generador de Equipos")
    if not jugadores:
        st.write("Registrá gente primero.")
    else:
        presentes = []
        for j in jugadores:
            if st.checkbox(f"{j['nombre']}", key=f"p_{j['id']}"):
                presentes.append(j)
        
        if st.button("⚖️ Armar"):
            if len(presentes) >= 2:
                import random
                random.shuffle(presentes)
                m = len(presentes) // 2
                ea, eb = presentes[:m], presentes[m:]
                
                c1, c2 = st.columns(2)
                with c1:
                    st.success("🔵 Equipo A")
                    for x in ea: st.write(f"- {x['nombre']}")
                with c2:
                    st.error("🔴 Equipo B")
                    for x in eb: st.write(f"- {x['nombre']}")
                
                msg = f"⚽ Equipos:\n\nA: " + ", ".join([x['nombre'] for x in ea])
                msg += f"\nB: " + ", ".join([x['nombre'] for x in eb])
                st.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}")
