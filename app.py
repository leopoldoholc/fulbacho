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

# =====================================================
# 🔐 AUTH & SYNC (Resumido para legibilidad)
# =====================================================
if "user" not in st.session_state: st.session_state.user = None

# ... (Funciones manejar_oauth, login, logout que ya tenés funcionando) ...
# [Mantené tus funciones de Auth aquí igual que antes]

def manejar_oauth():
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        try:
            supabase.auth.exchange_code_for_session({"auth_code": code})
            session = supabase.auth.get_session()
            if session and session.user: st.session_state.user = session.user
            st.query_params.clear()
            st.rerun()
        except: pass

manejar_oauth()
if not st.session_state.user:
    st.title("⚽ Fulbacho Pro")
    if st.button("Iniciar sesión con Google", type="primary"):
        import streamlit as st # Re-import necesario en algunos entornos
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": "https://fulbacho.streamlit.app"}
        })
        st.link_button("👉 Continuar con Google", response.url)
    st.stop()

user = st.session_state.user

# =====================================================
# 🏟️ PESTAÑA PARTIDOS (NUEVA CORE)
# =====================================================
def vista_partidos():
    st.header("📅 Gestión de Partidos")
    
    # Seleccionar Grupo
    admin_grupos = supabase.table("grupo_miembros").select("grupo_id, grupos(nombre, tipo_cancha)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    
    if not admin_grupos.data:
        st.info("Creá un grupo en la pestaña 'Grupos' para empezar a armar partidos.")
        return

    opciones_g = {g['grupo_id']: g['grupos']['nombre'] for g in admin_grupos.data if g['grupos']}
    g_sel = st.selectbox("Armar partido para:", options=list(opciones_g.keys()), format_func=lambda x: opciones_g[x], key="partido_g_sel")

    # Traer Miembros del Grupo
    res_m = supabase.table("grupo_miembros").select("usuarios(id, nombre)").eq("grupo_id", g_sel).execute()
    jugadores_disponibles = [m['usuarios'] for m in res_m.data if m['usuarios']]

    if not jugadores_disponibles:
        st.warning("No hay jugadores en este grupo.")
        return

    st.divider()
    
    col_lista, col_equipos = st.columns([1, 2])

    with col_lista:
        st.subheader("🙋‍♂️ Convocados")
        st.write("Seleccioná los 10/12 que juegan:")
        convocados = []
        for j in jugadores_disponibles:
            if st.checkbox(j['nombre'], key=f"conv_{j['id']}"):
                convocados.append(j)
        
        st.metric("Total convocados", len(convocados))

    with col_equipos:
        st.subheader("⚖️ Balance de Equipos")
        
        if len(convocados) < 2:
            st.info("Seleccioná al menos 2 jugadores para dividir equipos.")
        else:
            # Simulamos un nivel para la prueba (Luego esto vendrá de la DB)
            niveles = {}
            for c in convocados:
                niveles[c['id']] = st.slider(f"Nivel de {c['nombre']}", 1, 10, 5, key=f"lvl_{c['id']}")

            if st.button("🪄 Armar Equipos Equilibrados", type="primary", use_container_width=True):
                # Algoritmo de la serpiente (Snake Draft) simple
                ordenados = sorted(convocados, key=lambda x: niveles[x['id']], reverse=True)
                eq_a, eq_b = [], []
                
                for i, jug in enumerate(ordenados):
                    if i % 2 == 0: eq_a.append(jug)
                    else: eq_b.append(jug)
                
                # Visualización
                c1, c2 = st.columns(2)
                with c1:
                    st.success(f"🔵 EQUIPO A (Suma: {sum(niveles[j['id']] for j in eq_a)})")
                    for x in eq_a: st.write(f"🏃 {x['nombre']}")
                with c2:
                    st.error(f"🔴 EQUIPO B (Suma: {sum(niveles[j['id']] for j in eq_b)})")
                    for x in eq_b: st.write(f"🏃 {x['nombre']}")
                
                # Botón de WhatsApp
                txt_a = "\n".join([f"- {j['nombre']}" for j in eq_a])
                txt_b = "\n".join([f"- {j['nombre']}" for j in eq_b])
                mensaje = f"⚽ *FULBACHO CONFIRMADO*\n\n🔵 *EQUIPO A:*\n{txt_a}\n\n🔴 *EQUIPO B:*\n{txt_b}"
                st.link_button("📲 Enviar equipos por WhatsApp", f"https://wa.me/?text={urllib.parse.quote(mensaje)}")

# =====================================================
# [Mantené tus vistas_grupos, vista_perfil y vista_admin igual que antes]
# =====================================================

# (Agregué la pestaña de Partidos al final)
tabs = st.tabs(["🏟️ Grupos", "📝 Perfil", "⚙️ Admin", "📅 Partidos"])
with tabs[0]: 
    # [Tu lógica de vista_grupos]
    pass # Solo representativo, mantené tu código aquí
with tabs[1]:
    # [Tu lógica de vista_perfil]
    pass
with tabs[2]:
    # [Tu lógica de vista_admin]
    pass
with tabs[3]:
    vista_partidos()
