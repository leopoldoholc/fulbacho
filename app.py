import streamlit as st
from supabase import create_client
import urllib.parse
import json
import random
import string

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽", layout="wide")

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

# --- AUTH ---
if "user" not in st.session_state: st.session_state.user = None
if not st.session_state.user:
    # (Lógica de login simplificada para el ejemplo, mantener la anterior)
    st.title("⚽ Fulbacho Pro")
    if st.button("Iniciar sesión con Google"):
        # ... lógica oauth ...
        pass
    # Para pruebas, si ya estabas logueado, Streamlit mantiene la sesión
    user = st.session_state.get("user")
    if not user: st.stop()

user = st.session_state.user

# --- VISTA PARTIDOS (UX MEJORADA) ---
def vista_partidos():
    st.header("📅 Armado de Equipos")
    
    # 1. Obtener Grupos donde soy Admin
    res_admin = supabase.table("grupo_miembros").select("grupo_id, grupos(nombre, tipo_cancha)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not res_admin.data:
        st.info("No tenés permisos de administrador en ningún grupo.")
        return

    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in res_admin.data}
    idx = list(opciones.keys()).index(st.session_state.grupo_seleccionado) if st.session_state.grupo_seleccionado in opciones else 0
    
    g_sel = st.selectbox("Seleccionar Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx)
    grupo_info = next(g['grupos'] for g in res_admin.data if g['grupo_id'] == g_sel)
    
    # 2. Cargar Jugadores
    res_j = supabase.table("grupo_miembros").select("usuarios(id, nombre)").eq("grupo_id", g_sel).execute()
    jugadores = [j['usuarios'] for j in res_j.data if j['usuarios']]
    
    st.divider()
    
    # 3. Interfaz de Selección y Nivelación
    col_lista, col_niv = st.columns([1, 1.5])
    
    convocados_ids = []
    
    with col_lista:
        st.subheader("1. ¿Quiénes vienen?")
        st.checkbox("Seleccionar Todos", key="all_check", on_change=lambda: [st.session_state.update({f"c_{j['id']}": st.session_state.all_check}) for j in jugadores])
        
        for j in jugadores:
            if st.checkbox(j['nombre'], key=f"c_{j['id']}"):
                convocados_ids.append(j['id'])
    
    with col_niv:
        st.subheader("2. Nivelación (1-clic)")
        if not convocados_ids:
            st.warning("👈 Seleccioná a los jugadores en la lista para asignarles nivel.")
        else:
            niveles = {}
            for j_id in convocados_ids:
                nombre = next(j['nombre'] for j in jugadores if j['id'] == j_id)
                # Radio horizontal para selección rápida
                niveles[j_id] = st.radio(
                    f"Nivel de **{nombre}**",
                    options=range(1, 11),
                    index=4,
                    horizontal=True,
                    key=f"n_{j_id}"
                )
            
            st.divider()
            if st.button("🪄 Armar Equipos", type="primary", use_container_width=True):
                # Algoritmo de balanceo
                jug_objetos = [next(j for j in jugadores if j['id'] == j_id) for j_id in convocados_ids]
                ordenados = sorted(jug_objetos, key=lambda x: niveles[x['id']], reverse=True)
                
                equipo_a, equipo_b = [], []
                for i, jug in enumerate(ordenados):
                    if i % 2 == 0: equipo_a.append(jug)
                    else: equipo_b.append(jug)
                
                # Mostrar resultados
                c1, c2 = st.columns(2)
                with c1:
                    st.success("🔵 EQUIPO A")
                    for x in equipo_a: st.write(f"• {x['nombre']}")
                with c2:
                    st.error("🔴 EQUIPO B")
                    for x in equipo_b: st.write(f"• {x['nombre']}")
                
                # WhatsApp
                msg = f"⚽ *EQUIPOS:* \n\n*A:* " + ", ".join([j['nombre'] for j in equipo_a]) + "\n*B:* " + ", ".join([j['nombre'] for j in equipo_b])
                st.link_button("📲 Enviar por WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)

# --- NAVEGACIÓN (Radio Buttons horizontales) ---
st.sidebar.title("⚽ Fulbacho Pro")
vistas = ["🏟️ Grupos", "📝 Perfil", "⚙️ Admin", "📅 Partidos"]
nav = st.radio("Menu", vistas, index=vistas.index(st.session_state.vista_actual), horizontal=True, label_visibility="collapsed")

if nav != st.session_state.vista_actual:
    st.session_state.vista_actual = nav
    st.rerun()

if st.session_state.vista_actual == "📅 Partidos": vista_partidos()
# ... resto de vistas ...
